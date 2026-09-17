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
    merge_scraped_row, extract_email, filter_platform_rows,
    create_english_context, clean_platform_ui_text, normalize_follower_to_kmb, resolve_final_url
)

# --- CONFIGURATION ---
OUTPUT_CSV_FILE = PROJECT_ROOT / "data/output/linkedin_scraped_output.csv"


def classify_with_local_llm(headline_and_bio: str, name: str, model_provider=None, model_name=None):
    """
    Analyze LinkedIn professional profile using local LLM.
    """
    prompt = f"""
    Analyze this LinkedIn professional profile:
    Name: {name}
    Headline/About: {headline_and_bio}

    Return ONLY a valid JSON object with these exact keys:
    {{
        "Tags": ["tag1", "tag2", "tag3"],
        "PrimaryAITool": "Name of AI tool (e.g. Cursor, ChatGPT, Claude, Midjourney, LangChain, Runway) or null",
        "AIGCVerdict": "yes/no/hybrid",
        "Language": "Primary language of profile",
        "Region": "Country or location if identifiable, else null",
        "Evidence": "Brief quote/reason"
    }}
    """
    try:
        response_text = call_model(prompt, format="json", timeout=15, model_provider=model_provider, model_name=model_name)
        return json.loads(response_text)
    except Exception:
        combined = f"{name} {headline_and_bio}".lower()
        tools = [t.title() for t in ["chatgpt", "claude", "cursor", "langchain", "midjourney", "runway", "sora", "copilot"] if t in combined]
        return {
            "Tags": ["LinkedIn", "Tech", "AI Specialist"],
            "PrimaryAITool": tools[0] if tools else "GenAI",
            "AIGCVerdict": "yes" if any(k in combined for k in ["ai", "prompt", "llm", "generative", "synthetic"]) else "hybrid",
            "Language": "English",
            "Region": "Global",
            "Evidence": "Rule-based keyword fallback"
        }


def extract_linkedin_handle(raw_url: str):
    if not isinstance(raw_url, str) or not raw_url.strip():
        return None
    url = raw_url.strip()
    match = re.search(r'linkedin\.com/(?:in|company)/([a-zA-Z0-9_\.\-]+)', url)
    if match:
        return f"@{match.group(1).replace('/', '')}"
    return url.split('/')[-1] or url


# 2. LinkedIn Profile & Page Scraper via Playwright
def scrape_linkedin_profile(page, profile_url: str, model_provider=None, model_name=None):
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2.5)

        handle = extract_linkedin_handle(profile_url)

        # 1. Extract Public OpenGraph Meta Tags (Bypasses the login overlay)
        og_title = page.locator('meta[property="og:title"]').get_attribute("content") or ""
        og_desc = page.locator('meta[property="og:description"]').get_attribute("content") or ""
        
        # 2. Extract Visible Headline / Bio / About from Page DOM
        bio = og_desc
        name = og_title.split("-")[0].strip() if "-" in og_title else (og_title.split("|")[0].strip() or handle)
        
        try:
            # Check public profile card if rendered
            public_headline = page.locator('.top-card-layout__headline').first
            if public_headline.is_visible():
                bio = f"{public_headline.inner_text().strip()} | {og_desc}"
        except Exception:
            pass

        # 3. Extract Followers / Connections (Usually in public sub-headline or description)
        follower_count = "N/A"
        fol_match = re.search(r'([\d\.,]+[KkMmBb]?)\s*(?:followers|connections)', f"{og_desc} {page.inner_text('body')}", re.IGNORECASE)
        if fol_match:
            follower_count = fol_match.group(1)

        # 4. Extract Location / Region
        region = "Global"
        try:
            loc_elem = page.locator('.top-card-layout__first-subline').first
            if loc_elem.is_visible():
                region = loc_elem.inner_text().strip()
        except Exception:
            pass

        # AI Classification & Email Extraction
        ai_meta = classify_with_local_llm(bio, name, model_provider=model_provider, model_name=model_name)
        email = extract_email(bio)

        evidence = {
            "platform": "LinkedIn",
            "handle": handle,
            "name": name,
            "headline_preview": bio[:120],
            "aigc_verdict": ai_meta.get("AIGCVerdict", "hybrid"),
            "ai_reasoning": ai_meta.get("Evidence", "")
        }

        return {
            "Handle": handle or name,
            "FollowerCount": follower_count,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Region": region if region != "Global" else ai_meta.get("Region", "Global"),
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": profile_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "hybrid"),
            "Notes": f"LinkedIn public scrape: followers/conn={follower_count}; headline={bio[:60].strip()}",
            "FeedURL": f"{profile_url}/recent-activity/all/",
            "ContactSourceURL": profile_url if email != "not exposed" else "",
            "EvidenceJSON": json.dumps(evidence)
        }

    except Exception as e:
        print(f"[-] Error scraping LinkedIn {profile_url}: {e}")
        return None


# --- 3. BATCH PROCESSOR ---
def main(limit=None, model_provider=None, model_name=None):
    if not INPUT_CSV_FILE.exists():
        print(f"[!] File '{INPUT_CSV_FILE}' not found. Please create it or verify the path.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = load_and_clean_csv(INPUT_CSV_FILE)
    platform_col, url_col = get_column_names(df)

    # Filter strictly for LinkedIn rows
    li_rows = filter_platform_rows(df, platform_col, url_col, "linkedin", "linkedin.com")
    if limit is not None:
        li_rows = li_rows.head(limit)
    print(f"[+] Found {len(li_rows)} LinkedIn profiles to scrape.\n")

    if li_rows.empty:
        print("[!] No LinkedIn profiles found to process.")
        return

    updated_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = create_english_context(browser)
        page = context.new_page()

        for idx, (original_index, row) in enumerate(li_rows.iterrows(), 1):
            url = str(row[url_col]).strip()
            print(f"[{idx}/{len(li_rows)}] Scraping LinkedIn: {url}")

            scraped_data = scrape_linkedin_profile(page, url, model_provider=model_provider, model_name=model_name)
            row_dict = row.to_dict()
            row_dict["Platform"] = "LinkedIn"
            row_dict = merge_scraped_row(row_dict, scraped_data)
            updated_rows.append(row_dict)
            time.sleep(2.5)  # Wait 2.5s between requests to prevent IP blocks

        browser.close()

    # Save to CSV
    final_df = pd.DataFrame(updated_rows)
    final_df = enforce_target_columns(final_df)
    final_df.to_csv(OUTPUT_CSV_FILE, index=False)
    print(f"\n[✓] Completed! Saved {len(final_df)} LinkedIn records to '{OUTPUT_CSV_FILE}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max LinkedIn profiles to process")
    parser.add_argument("--model-provider", type=str, default=None, help="Override MODEL_PROVIDER for this run")
    parser.add_argument("--model-name", type=str, default=None, help="Override MODEL_NAME for this run")
    args = parser.parse_args()
    main(limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)
