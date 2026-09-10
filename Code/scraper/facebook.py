import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import unquote
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
OUTPUT_CSV_FILE = PROJECT_ROOT / "data/output/facebook_scraped_output.csv"


def classify_with_local_llm(bio: str, handle: str, model_provider=None, model_name=None):
    """
    Analyze Facebook page/creator's name and bio using local LLM.
    """
    prompt = f"""
    Analyze this Facebook page/creator's name and bio.
    Name/Handle: {handle}
    Bio/Intro: {bio}

    Return ONLY a valid JSON object with these exact keys:
    {{
        "Tags": ["tag1", "tag2", "tag3"],
        "PrimaryAITool": "Name of AI tool (e.g. Midjourney, Sora, Runway, ChatGPT) or null",
        "AIGCVerdict": "yes/no/hybrid",
        "Language": "Primary language of content",
        "Evidence": "Brief quote/reason"
    }}
    """
    try:
        response_text = call_model(prompt, format="json", timeout=15, model_provider=model_provider, model_name=model_name)
        return json.loads(response_text)
    except Exception:
        combined = f"{handle} {bio}".lower()
        tools = [t.title() for t in ["midjourney", "sora", "runway", "kling", "luma", "chatgpt", "claude", "stable diffusion"] if t in combined]
        return {
            "Tags": ["Facebook", "AIGC", "Creator"],
            "PrimaryAITool": tools[0] if tools else "GenAI",
            "AIGCVerdict": "yes" if any(k in combined for k in ["ai", "synthetic", "generative", "midjourney", "bot"]) else "hybrid",
            "Language": "English",
            "Evidence": "Rule-based keyword fallback"
        }


def extract_facebook_username(raw_val: str):
    if not isinstance(raw_val, str) or not raw_val.strip():
        return None
    val = raw_val.strip()
    match = re.search(r'facebook\.com/([a-zA-Z0-9_\.\-]+)', val)
    if match:
        name = match.group(1)
        if name not in ["profile.php", "pages", "groups", "share"]:
            return f"@{name}"
    return val.split('/')[-1] or val


# Clean FB redirect links (e.g., l.facebook.com/l.php?u=...)
def clean_facebook_url(url: str):
    if "l.facebook.com/l.php" in url:
        match = re.search(r'[?&]u=([^&]+)', url)
        if match:
            return unquote(match.group(1))
    return url


# 2. Facebook Profile & Page Scraper via Playwright
def scrape_facebook_profile(page, profile_url: str, model_provider=None, model_name=None):
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2.5)

        handle = extract_facebook_username(profile_url)

        # 1. Extract OpenGraph Meta Tags (Most reliable without logging in)
        og_title = page.locator('meta[property="og:title"]').get_attribute("content") or ""
        og_desc = page.locator('meta[property="og:description"]').get_attribute("content") or ""
        
        # 2. Extract Followers / Likes
        follower_count = "N/A"
        # Often in og:description: "X likes · Y talking about this" or "X followers"
        fol_match = re.search(r'([\d\.,]+[KkMmBb]?)\s*(?:followers|likes)', og_desc, re.IGNORECASE)
        if fol_match:
            follower_count = fol_match.group(1)
        else:
            # Try searching page text
            body_text = page.inner_text("body")
            fol_match_body = re.search(r'([\d\.,]+[KkMmBb]?)\s*followers', body_text, re.IGNORECASE)
            if fol_match_body:
                follower_count = fol_match_body.group(1)

        # 3. Extract Bio / Intro
        bio = og_desc
        try:
            intro_elem = page.locator('div[role="main"]').inner_text()
            if intro_elem and len(intro_elem) > len(bio):
                bio = intro_elem[:300]
        except Exception:
            pass

        # 4. Extract External Link
        external_link = ""
        try:
            links = page.locator('a[href*="http"]').all()
            for l in links:
                href = l.get_attribute("href") or ""
                if "l.facebook.com" in href:
                    external_link = clean_facebook_url(href)
                    break
                elif not any(d in href for d in ["facebook.com", "fb.com", "instagram.com"]):
                    external_link = href
                    break
        except Exception:
            pass

        # AI Classification & Email Discovery
        ai_meta = classify_with_local_llm(bio, handle or og_title, model_provider=model_provider, model_name=model_name)
        email = extract_email(bio)

        evidence = {
            "platform": "Facebook",
            "handle": handle,
            "title": og_title,
            "bio_preview": bio[:100],
            "external_link": external_link,
            "aigc_verdict": ai_meta.get("AIGCVerdict", "yes"),
            "ai_reasoning": ai_meta.get("Evidence", "")
        }

        return {
            "Handle": handle or og_title,
            "FollowerCount": follower_count,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": external_link or profile_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "yes"),
            "Notes": f"Facebook scrape: followers={follower_count}; bio_preview={bio[:60].strip()}",
            "FeedURL": profile_url,
            "ContactSourceURL": profile_url if email != "not exposed" else external_link,
            "EvidenceJSON": json.dumps(evidence)
        }

    except Exception as e:
        print(f"[-] Error scraping Facebook {profile_url}: {e}")
        return None


# --- 3. BATCH PROCESSOR ---
def main(limit=None, model_provider=None, model_name=None):
    if not INPUT_CSV_FILE.exists():
        print(f"[!] File '{INPUT_CSV_FILE}' not found. Please create it or verify the path.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = load_and_clean_csv(INPUT_CSV_FILE)
    platform_col, url_col = get_column_names(df)

    # Filter strictly for Facebook rows
    fb_rows = filter_platform_rows(df, platform_col, url_col, "facebook", "facebook.com")
    if limit is not None:
        fb_rows = fb_rows.head(limit)
    print(f"[+] Found {len(fb_rows)} Facebook profiles to scrape.\n")

    if fb_rows.empty:
        print("[!] No Facebook profiles found to process.")
        return

    updated_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        for idx, (original_index, row) in enumerate(fb_rows.iterrows(), 1):
            url = str(row[url_col]).strip()
            print(f"[{idx}/{len(fb_rows)}] Scraping Facebook: {url}")

            scraped_data = scrape_facebook_profile(page, url, model_provider=model_provider, model_name=model_name)
            row_dict = row.to_dict()
            row_dict["Platform"] = "Facebook"
            row_dict = merge_scraped_row(row_dict, scraped_data)
            updated_rows.append(row_dict)
            time.sleep(2)  # Wait 2s to avoid aggressive Facebook IP throttling

        browser.close()

    # Save to CSV
    final_df = pd.DataFrame(updated_rows)
    final_df = enforce_target_columns(final_df)
    final_df.to_csv(OUTPUT_CSV_FILE, index=False)
    print(f"\n[✓] Completed! Saved {len(final_df)} Facebook records to '{OUTPUT_CSV_FILE}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max Facebook profiles to process")
    parser.add_argument("--model-provider", type=str, default=None, help="Override MODEL_PROVIDER for this run")
    parser.add_argument("--model-name", type=str, default=None, help="Override MODEL_NAME for this run")
    args = parser.parse_args()
    main(limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)
