import os
import re
import json
import argparse
import time
import requests
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from pathlib import Path

from model_client import call_model
from common import (
    PROJECT_ROOT, INPUT_CSV_FILE, TARGET_COLUMNS,
    load_and_clean_csv, get_column_names, enforce_target_columns,
    merge_scraped_row, extract_email, filter_platform_rows,
    create_english_context, clean_platform_ui_text, normalize_follower_to_kmb, resolve_final_url
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- CONFIGURATION ---
INPUT_CSV_FILE = PROJECT_ROOT / "data/input/input_channels.csv"
OUTPUT_CSV_FILE = PROJECT_ROOT / "data/output/threads_scraped_output.csv"

# 1. AI Classifier
def classify_with_local_llm(bio: str, handle: str, model_provider=None, model_name=None):
    prompt = f"""
    Analyze this Threads creator's handle and bio.
    Handle: {handle}
    Bio: {bio}

    Return ONLY a valid JSON object with these exact keys:
    {{
        "Tags": ["tag1", "tag2", "tag3"],
        "PrimaryAITool": "Name of AI tool (e.g. Midjourney, Sora, Claude, Runway, ChatGPT) or null",
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
        tools = [t.title() for t in ["midjourney", "sora", "runway", "kling", "luma", "chatgpt", "claude", "cursor"] if t in combined]
        return {
            "Tags": ["Threads", "AIGC", "Creator"],
            "PrimaryAITool": tools[0] if tools else "GenAI",
            "AIGCVerdict": "yes" if any(k in combined for k in ["ai", "sora", "synthetic", "bot", "genai"]) else "hybrid",
            "Language": "English",
            "Evidence": "Rule-based keyword fallback"
        }

def extract_email(text: str):
    if not text:
        return "not exposed"
    match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(text))
    return match.group(0) if match else "not exposed"

def extract_threads_username(raw_val: str):
    if not isinstance(raw_val, str) or not raw_val.strip():
        return None
    val = raw_val.strip()
    match = re.search(r'threads\.(?:net|com)/(@[a-zA-Z0-9_\.\-]+)', val)
    if match:
        return match.group(1)
    if val.startswith("@"):
        return val
    return f"@{val}"

# 2. Standalone Threads Scraper via Playwright
def scrape_threads_profile(page, profile_url: str, model_provider=None, model_name=None):
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2.5)  # Allow dynamic client rendering

        handle = extract_threads_username(profile_url)

        # Extract Bio
        bio = ""
        try:
            # Look for meta description or bio container text
            meta_desc = page.locator('meta[property="og:description"]').get_attribute("content")
            if meta_desc:
                bio = meta_desc.strip()
        except Exception:
            pass

        # Extract Followers (Often in og:description or visible profile header text)
        follower_count = "N/A"
        try:
            # Check page body/header for follower counts (e.g., '12.5K followers' or '345 followers')
            body_text = page.inner_text("body")
            fol_match = re.search(r'([\d\.,]+[KkMmBb]?)\s*followers', body_text, re.IGNORECASE)
            if fol_match:
                follower_count = fol_match.group(1)
        except Exception:
            pass

        # Extract External Link
        external_link = ""
        try:
            links = page.locator('a[href*="http"]').all()
            for l in links:
                href = l.get_attribute("href") or ""
                if not any(domain in href for domain in ["threads.net", "instagram.com", "facebook.com"]):
                    external_link = href
                    break
        except Exception:
            pass

        # AI Classification
        ai_meta = classify_with_local_llm(bio, handle or "", model_provider=model_provider, model_name=model_name)
        email = extract_email(bio)

        evidence = {
            "platform": "Threads",
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
            "Notes": f"Threads scrape: followers={follower_count}; bio_preview={bio[:60]}",
            "FeedURL": profile_url,
            "ContactSourceURL": profile_url if email != "not exposed" else external_link,
            "EvidenceJSON": json.dumps(evidence)
        }

    except Exception as e:
        print(f"[-] Error scraping Threads {profile_url}: {e}")
        return None

# --- 3. BATCH PROCESSOR ---
def main(limit=None, model_provider=None, model_name=None):
    if not INPUT_CSV_FILE.exists():
        print(f"[!] File '{INPUT_CSV_FILE}' not found. Please create it or verify the path.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = pd.read_csv(INPUT_CSV_FILE)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = [c.strip() for c in df.columns]

    platform_col = "Platform" if "Platform" in df.columns else df.columns[2]
    url_col = "ProfileURL" if "ProfileURL" in df.columns else df.columns[0]

    # Filter strictly for Threads rows (Column C == Threads or URL contains threads.net)
    threads_mask = (
        df[platform_col].astype(str).str.strip().str.lower().isin(["threads", "thread"]) |
        df[url_col].astype(str).str.contains("threads.net", case=False, na=False)
    )

    threads_rows = df[threads_mask].copy()
    print(f"[+] Found {len(threads_rows)} Threads profiles to scrape.\n")

    if threads_rows.empty:
        print("[!] No Threads profiles found to process.")
        return

    updated_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = create_english_context(browser)
        page = context.new_page()

        for idx, (original_index, row) in enumerate(threads_rows.iterrows(), 1):
            url = str(row[url_col]).strip()
            print(f"[{idx}/{len(threads_rows)}] Scraping Threads: {url}")

            scraped_data = scrape_threads_profile(page, url, model_provider=model_provider, model_name=model_name)

            row_dict = row.to_dict()
            row_dict["Platform"] = "Threads"

            if scraped_data:
                row_dict["Name/Handle"] = scraped_data["Handle"]
                row_dict["FollowerCount"] = scraped_data["FollowerCount"]
                if row_dict.get("Email") in [None, "", "not exposed"]:
                    row_dict["Email"] = scraped_data["Email"]
                row_dict["LastScrapedAt"] = scraped_data["LastScrapedAt"]
                row_dict["Language"] = scraped_data["Language"]
                row_dict["PrimaryAITool"] = scraped_data["PrimaryAITool"] or row_dict.get("PrimaryAITool")
                row_dict["SampleContentURL"] = scraped_data["SampleContentURL"] or row_dict.get("SampleContentURL")
                row_dict["AIGCVerdict"] = scraped_data["AIGCVerdict"]
                row_dict["Notes"] = scraped_data["Notes"]
                row_dict["FeedURL"] = scraped_data["FeedURL"]
                row_dict["ContactSourceURL"] = scraped_data["ContactSourceURL"]
                row_dict["EvidenceJSON"] = scraped_data["EvidenceJSON"]

            updated_rows.append(row_dict)
            time.sleep(1.5)

        browser.close()

    # Save to CSV
    final_df = pd.DataFrame(updated_rows)
    target_columns = [
        "ProfileURL", "Name/Handle", "Platform", "FollowerCount", "Email", "Tags",
        "OutreachStatus", "LastScrapedAt", "Region", "Language", "PrimaryAITool",
        "SampleContentURL", "AIGCVerdict", "DiscoveredAt", "Source", "Notes",
        "FeedURL", "ContactSourceURL", "EvidenceJSON"
    ]
    for col in target_columns:
        if col not in final_df.columns:
            final_df[col] = None

    final_df = final_df[target_columns]
    final_df.to_csv(OUTPUT_CSV_FILE, index=False)
    print(f"\n[✓] Completed! Saved {len(final_df)} Threads records to '{OUTPUT_CSV_FILE}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max Threads profiles to process")
    parser.add_argument("--model-provider", type=str, default=None, help="Override MODEL_PROVIDER for this run")
    parser.add_argument("--model-name", type=str, default=None, help="Override MODEL_NAME for this run")
    args = parser.parse_args()
    main(limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)