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
OUTPUT_CSV_FILE = PROJECT_ROOT / "data/output/reddit_scraped_output.csv"


def classify_with_local_llm(bio: str, sample_text: str, username: str, model_provider=None, model_name=None):
    """
    Analyze Reddit user profile and their recent content using local LLM.
    """
    prompt = f"""
    Analyze this Reddit user profile and their recent content:
    Username: u/{username}
    Bio/Description: {bio}
    Sample Post: {sample_text}

    Return ONLY a valid JSON object with these exact keys:
    {{
        "Tags": ["tag1", "tag2", "tag3"],
        "PrimaryAITool": "Name of AI tool (e.g. ComfyUI, Stable Diffusion, Midjourney, FLUX, Sora, Runway, ChatGPT) or null",
        "AIGCVerdict": "yes/no/hybrid",
        "Language": "Primary language of content",
        "Region": "Country or location if detectable, else null",
        "Evidence": "Brief quote/reason"
    }}
    """
    try:
        response_text = call_model(prompt, format="json", timeout=15, model_provider=model_provider, model_name=model_name)
        return json.loads(response_text)
    except Exception:
        combined = f"{username} {bio} {sample_text}".lower()
        tools = [t.title() for t in ["comfyui", "stable diffusion", "flux", "midjourney", "sora", "runway", "kling", "luma", "chatgpt", "claude"] if t in combined]
        return {
            "Tags": ["Reddit", "AIGC", "Tech"],
            "PrimaryAITool": tools[0] if tools else "GenAI",
            "AIGCVerdict": "yes" if any(k in combined for k in ["ai", "synthetic", "diffusion", "comfyui", "lora", "render"]) else "hybrid",
            "Language": "English",
            "Region": "Global",
            "Evidence": "Rule-based keyword fallback"
        }


def extract_reddit_username(raw_val: str):
    if not isinstance(raw_val, str) or not raw_val.strip():
        return None
    val = raw_val.strip()
    match = re.search(r'reddit\.com/user/([a-zA-Z0-9_\-]+)', val)
    if match:
        return match.group(1)
    match_u = re.search(r'reddit\.com/u/([a-zA-Z0-9_\-]+)', val)
    if match_u:
        return match_u.group(1)
    if val.startswith("u/"):
        return val.replace("u/", "")
    return val.split('/')[-1] or val


# 2. Reddit Scraper via Playwright Browser Automation
def scrape_reddit_profile_playwright(page, username: str, model_provider=None, model_name=None):
    profile_url = f"https://www.reddit.com/user/{username}/"
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2)

        # A. Extract OpenGraph Meta Tags
        og_title = page.locator('meta[property="og:title"]').get_attribute("content") or ""
        og_desc = page.locator('meta[property="og:description"]').get_attribute("content") or ""

        # B. Extract Karma & Stats from public page
        page_text = page.inner_text("body")
        karma_match = re.search(r'([\d\.,]+[KkMmBb]?)\s*(?:karma|Post Karma|Comment Karma)', page_text, re.IGNORECASE)
        follower_count_str = f"{karma_match.group(1)} karma" if karma_match else "N/A"

        # C. Extract Bio
        bio = og_desc
        try:
            # Try to grab bio description block if present
            desc_elem = page.locator('shreddit-profile-about').first
            if desc_elem.is_visible():
                bio = f"{desc_elem.inner_text().strip()} | {og_desc}"
        except Exception:
            pass

        # D. Extract Top Recent Post
        sample_post_title = ""
        try:
            first_post = page.locator('a[slot="full-post-link"]').first
            if first_post.is_visible():
                sample_post_title = first_post.inner_text().strip()
        except Exception:
            pass

        # AI Classification & Email Extraction
        ai_meta = classify_with_local_llm(bio, sample_post_title, username, model_provider=model_provider, model_name=model_name)
        email = extract_email(bio)

        evidence = {
            "platform": "Reddit",
            "handle": f"u/{username}",
            "title": og_title,
            "karma": follower_count_str,
            "bio_preview": bio[:120],
            "recent_post": sample_post_title[:80],
            "aigc_verdict": ai_meta.get("AIGCVerdict", "yes"),
            "ai_reasoning": ai_meta.get("Evidence", "")
        }

        return {
            "Handle": f"u/{username}",
            "FollowerCount": follower_count_str,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Region": ai_meta.get("Region") or "Global",
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": profile_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "yes"),
            "Notes": f"Reddit scrape: karma={follower_count_str}; bio={bio[:60].strip()}",
            "FeedURL": f"https://www.reddit.com/user/{username}/submitted.rss",
            "ContactSourceURL": profile_url if email != "not exposed" else "",
            "EvidenceJSON": json.dumps(evidence)
        }

    except Exception as e:
        print(f"[-] Error scraping u/{username}: {e}")
        return None


# --- 3. BATCH PROCESSOR ---
def main(limit=None, model_provider=None, model_name=None):
    if not INPUT_CSV_FILE.exists():
        print(f"[!] File '{INPUT_CSV_FILE}' not found. Please create it or verify the path.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = load_and_clean_csv(INPUT_CSV_FILE)
    platform_col, url_col = get_column_names(df)

    # Filter strictly for Reddit rows
    reddit_rows = filter_platform_rows(df, platform_col, url_col, "reddit", "reddit.com")
    if limit is not None:
        reddit_rows = reddit_rows.head(limit)
    print(f"[+] Found {len(reddit_rows)} Reddit profiles to scrape.\n")

    if reddit_rows.empty:
        print("[!] No Reddit profiles found to process.")
        return

    updated_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = create_english_context(browser)
        page = context.new_page()

        for idx, (original_index, row) in enumerate(reddit_rows.iterrows(), 1):
            url = str(row[url_col]).strip()
            username = extract_reddit_username(url)

            if not username:
                print(f"[{idx}/{len(reddit_rows)}] Skipping invalid username: {url}")
                updated_rows.append(row.to_dict())
                continue

            print(f"[{idx}/{len(reddit_rows)}] Scraping Reddit: u/{username}")
            scraped_data = scrape_reddit_profile_playwright(page, username, model_provider=model_provider, model_name=model_name)
            row_dict = row.to_dict()
            row_dict["Platform"] = "Reddit"
            row_dict = merge_scraped_row(row_dict, scraped_data)
            updated_rows.append(row_dict)
            time.sleep(1.5)  # Respect rate limits

        browser.close()

    # Save to CSV
    final_df = pd.DataFrame(updated_rows)
    final_df = enforce_target_columns(final_df)
    final_df.to_csv(OUTPUT_CSV_FILE, index=False)
    print(f"\n[✓] Completed! Saved {len(final_df)} Reddit records to '{OUTPUT_CSV_FILE}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max Reddit profiles to process")
    parser.add_argument("--model-provider", type=str, default=None, help="Override MODEL_PROVIDER for this run")
    parser.add_argument("--model-name", type=str, default=None, help="Override MODEL_NAME for this run")
    args = parser.parse_args()
    main(limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)
