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
OUTPUT_CSV_FILE = PROJECT_ROOT / "data/output/tiktok_scraped_output.csv"


def classify_with_local_llm(bio: str, handle: str, model_provider=None, model_name=None):
    """
    Analyze TikTok creator's handle and bio using local LLM.
    """
    prompt = f"""
    Analyze this TikTok creator's handle and bio.
    Handle: {handle}
    Bio: {bio}

    Return ONLY a valid JSON object with these exact keys:
    {{
        "Tags": ["tag1", "tag2", "tag3"],
        "PrimaryAITool": "Name of AI tool (e.g. Midjourney, Sora, CapCut AI, Runway, Kling) or null",
        "AIGCVerdict": "yes/no/hybrid",
        "Language": "Primary language of content",
        "Evidence": "Brief quote/reason"
    }}
    """
    try:
        response_text = call_model(prompt, format="json", timeout=15, model_provider=model_provider, model_name=model_name)
        return json.loads(response_text)
    except Exception:
        # Fallback if Ollama is offline
        combined = f"{handle} {bio}".lower()
        tools = [t.title() for t in ["midjourney", "sora", "runway", "kling", "luma", "capcut", "chatgpt"] if t in combined]
        return {
            "Tags": ["TikTok", "AIGC", "Creator"],
            "PrimaryAITool": tools[0] if tools else "GenAI",
            "AIGCVerdict": "yes" if any(k in combined for k in ["ai", "sora", "synthetic", "bot", "diffusion"]) else "hybrid",
            "Language": "English",
            "Evidence": "Rule-based keyword fallback"
        }


# 2. Standalone TikTok Scraper via Playwright
def scrape_tiktok_profile(page, profile_url: str, model_provider=None, model_name=None):
    try:
        # Navigate to profile with custom user-agent
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2)  # Allow dynamic JS elements to render

        # Extract handle / username
        handle_match = re.search(r'tiktok\.com/(@[a-zA-Z0-9_\.\-]+)', profile_url)
        handle = handle_match.group(1) if handle_match else profile_url.split('/')[-1]

        # Extract Followers
        follower_count = "N/A"
        try:
            follower_elem = page.locator('[data-e2e="followers-count"]').first
            if follower_elem.is_visible():
                follower_count = follower_elem.inner_text().strip()
        except Exception:
            pass

        # Extract Bio Signature
        bio = ""
        try:
            bio_elem = page.locator('[data-e2e="user-bio"]').first
            if bio_elem.is_visible():
                bio = bio_elem.inner_text().strip()
        except Exception:
            pass

        # Extract External Bio Link (Linktree / Beacons / Website)
        external_link = ""
        try:
            link_elem = page.locator('[data-e2e="user-link"]').first
            if link_elem.is_visible():
                external_link = link_elem.inner_text().strip()
        except Exception:
            pass

        # AI Classification
        ai_meta = classify_with_local_llm(bio, handle, model_provider=model_provider, model_name=model_name)
        email = extract_email(bio)

        evidence = {
            "platform": "TikTok",
            "handle": handle,
            "bio_preview": bio[:100],
            "external_link": external_link,
            "aigc_verdict": ai_meta.get("AIGCVerdict", "yes"),
            "ai_reasoning": ai_meta.get("Evidence", "")
        }

        return {
            "Handle": handle,
            "FollowerCount": follower_count,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": external_link or profile_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "yes"),
            "Notes": f"TikTok scrape: followers={follower_count}; bio_link={external_link or 'none'}",
            "FeedURL": profile_url,
            "ContactSourceURL": profile_url if email != "not exposed" else external_link,
            "EvidenceJSON": json.dumps(evidence)
        }

    except Exception as e:
        print(f"[-] Error scraping {profile_url}: {e}")
        return None

# --- 3. BATCH PROCESSOR ---
def main(limit=None, model_provider=None, model_name=None):
    if not INPUT_CSV_FILE.exists():
        print(f"[!] File '{INPUT_CSV_FILE}' not found. Please create it or verify the path.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = load_and_clean_csv(INPUT_CSV_FILE)
    platform_col, url_col = get_column_names(df)

    # Filter strictly for TikTok rows
    tiktok_rows = filter_platform_rows(df, platform_col, url_col, "tiktok", "tiktok.com")
    if limit is not None:
        tiktok_rows = tiktok_rows.head(limit)
    print(f"[+] Found {len(tiktok_rows)} TikTok profiles to scrape.\n")

    if tiktok_rows.empty:
        print("[!] No TikTok profiles found to process.")
        return

    updated_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = create_english_context(browser)
        page = context.new_page()

        for idx, (original_index, row) in enumerate(tiktok_rows.iterrows(), 1):
            url = str(row[url_col]).strip()
            print(f"[{idx}/{len(tiktok_rows)}] Scraping TikTok: {url}")

            scraped_data = scrape_tiktok_profile(page, url)
            row_dict = row.to_dict()
            row_dict["Platform"] = "TikTok"
            row_dict = merge_scraped_row(row_dict, scraped_data)
            updated_rows.append(row_dict)

        browser.close()

    # Save to CSV
    final_df = pd.DataFrame(updated_rows)
    final_df = enforce_target_columns(final_df)
    final_df.to_csv(OUTPUT_CSV_FILE, index=False)
    print(f"\n[✓] Completed! Saved {len(final_df)} TikTok records to '{OUTPUT_CSV_FILE}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max TikTok profiles to process")
    parser.add_argument("--model-provider", type=str, default=None, help="Override MODEL_PROVIDER for this run")
    parser.add_argument("--model-name", type=str, default=None, help="Override MODEL_NAME for this run")
    args = parser.parse_args()
    main(limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)