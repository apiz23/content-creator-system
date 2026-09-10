import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from pathlib import Path
import argparse

from model_client import call_model
from common import (
    PROJECT_ROOT, INPUT_CSV_FILE, TARGET_COLUMNS,
    load_and_clean_csv, get_column_names, enforce_target_columns,
    merge_scraped_row, extract_email, filter_platform_rows
)

# --- CONFIGURATION ---
OUTPUT_CSV_FILE = PROJECT_ROOT / "data/output/instagram_scraped_output.csv"


def classify_with_local_llm(bio: str, handle: str, model_provider=None, model_name=None):
    """
    Analyze Instagram creator's handle and bio using local LLM.
    """
    prompt = f"""
    Analyze this Instagram creator's handle and bio.
    Handle: {handle}
    Bio: {bio}

    Return ONLY a valid JSON object:
    {{
        "Tags": ["tag1", "tag2", "tag3"],
        "PrimaryAITool": "Name of AI tool (e.g. Midjourney, Sora, Runway, Kling) or null",
        "AIGCVerdict": "yes/no/hybrid",
        "Language": "Primary language",
        "Evidence": "Brief reason"
    }}
    """
    try:
        response_text = call_model(prompt, format="json", timeout=15, model_provider=model_provider, model_name=model_name)
        return json.loads(response_text)
    except Exception:
        combined = f"{handle} {bio}".lower()
        tools = [t.title() for t in ["midjourney", "sora", "runway", "kling", "luma", "chatgpt"] if t in combined]
        return {
            "Tags": ["Instagram", "AIGC"],
            "PrimaryAITool": tools[0] if tools else "GenAI",
            "AIGCVerdict": "yes" if any(k in combined for k in ["ai", "synthetic", "midjourney", "art"]) else "hybrid",
            "Language": "English",
            "Evidence": "Rule-based fallback"
        }


def scrape_instagram_playwright(page, profile_url: str, model_provider=None, model_name=None):
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2.5)

        # 1. Extract metadata from OpenGraph tags (Bypasses UI rate limits)
        og_desc = page.locator('meta[property="og:description"]').get_attribute("content") or ""
        if not og_desc:
            # fallback: try page meta description and title
            og_desc = (page.locator('meta[name="description"]').get_attribute("content") or "") + " " + (page.title() or "")
            # Also try grabbing the description from the JSON-LD or other meta tags
            desc_json = page.locator('script[type="application/ld+json"]').content()
            if desc_json:
                try:
                    import json as _json
                    ld = _json.loads(desc_json)
                    if isinstance(ld, dict) and ld.get("description"):
                        og_desc = ld["description"]
                except Exception:
                    pass
        
        # Format usually: "10K Followers, 150 Following, 42 Posts - See Instagram photos..."
        follower_count = "N/A"
        fol_match = re.search(r'([\d\.,]+[KkMmBb]?)\s*Followers', og_desc, re.IGNORECASE)
        if fol_match:
            follower_count = fol_match.group(1)

        # 2. Extract Bio Text
        bio = ""
        try:
            # Try to grab bio element or fallback to og:description
            bio_elem = page.locator('header section').first
            if bio_elem.is_visible():
                bio = bio_elem.inner_text()
            else:
                bio = og_desc
        except Exception:
            bio = og_desc

        handle_match = re.search(r'instagram\.com/([a-zA-Z0-9_\.]+)', profile_url)
        handle = f"@{handle_match.group(1).replace('/', '')}" if handle_match else profile_url.split('/')[-1]

        # 3. AI classification & Email extraction
        ai_meta = classify_with_local_llm(bio, handle, model_provider=model_provider, model_name=model_name)
        email = extract_email(bio)

        evidence = {
            "platform": "Instagram",
            "handle": handle,
            "og_description": og_desc[:120],
            "aigc_verdict": ai_meta.get("AIGCVerdict", "yes")
        }

        return {
            "Handle": handle,
            "FollowerCount": follower_count,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": profile_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "yes"),
            "Notes": f"Playwright scrape: followers={follower_count}",
            "FeedURL": profile_url,
            "ContactSourceURL": profile_url if email != "not exposed" else "",
            "EvidenceJSON": json.dumps(evidence)
        }
    except Exception as e:
        print(f"[-] Playwright error on {profile_url}: {e}")
        return None


def main(limit=None, model_provider=None, model_name=None):
    if not INPUT_CSV_FILE.exists():
        print(f"[!] File '{INPUT_CSV_FILE}' not found. Please create it or verify the path.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = load_and_clean_csv(INPUT_CSV_FILE)
    platform_col, url_col = get_column_names(df)

    # Filter strictly for Instagram rows
    ig_rows = filter_platform_rows(df, platform_col, url_col, "instagram", "instagram.com")
    if limit is not None:
        ig_rows = ig_rows.head(limit)
    print(f"[+] Found {len(ig_rows)} Instagram profiles to scrape with Playwright.\n")

    updated_rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for idx, (original_index, row) in enumerate(ig_rows.iterrows(), 1):
            url = str(row[url_col]).strip()
            print(f"[{idx}/{len(ig_rows)}] Scraping Instagram: {url}")

            scraped_data = scrape_instagram_playwright(page, url, model_provider=model_provider, model_name=model_name)
            row_dict = row.to_dict()
            row_dict["Platform"] = "Instagram"
            row_dict = merge_scraped_row(row_dict, scraped_data)
            updated_rows.append(row_dict)
            time.sleep(3)  # Wait 3 seconds between profiles

        browser.close()

    final_df = pd.DataFrame(updated_rows)
    final_df = enforce_target_columns(final_df)
    final_df.to_csv(OUTPUT_CSV_FILE, index=False)
    print(f"\n[✓] Completed! Saved to '{OUTPUT_CSV_FILE}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max Instagram profiles to process")
    parser.add_argument("--model-provider", type=str, default=None, help="Override MODEL_PROVIDER for this run")
    parser.add_argument("--model-name", type=str, default=None, help="Override MODEL_NAME for this run")
    args = parser.parse_args()
    main(limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)
