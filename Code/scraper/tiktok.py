import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
INPUT_CSV_FILE = "input_channels.csv"           # Input CSV with TikTok URLs
OUTPUT_CSV_FILE = "tiktok_scraped_output.csv"   # Output updated CSV

# 1. Zero-Cost Local AI Classifier via Ollama
def classify_with_local_llm(bio: str, handle: str):
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
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3.5:latest",
                "prompt": prompt,
                "format": "json",
                "stream": False
            },
            timeout=15
        )
        return json.loads(res.json().get("response", "{}"))
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

def extract_email(text: str):
    if not text:
        return "not exposed"
    match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(text))
    return match.group(0) if match else "not exposed"

# 2. Standalone TikTok Scraper via Playwright
def scrape_tiktok_profile(page, profile_url: str):
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
        ai_meta = classify_with_local_llm(bio, handle)
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
def main():
    if not os.path.exists(INPUT_CSV_FILE):
        print(f"[!] File '{INPUT_CSV_FILE}' not found. Please create it or verify the path.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = pd.read_csv(INPUT_CSV_FILE)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = [c.strip() for c in df.columns]

    platform_col = "Platform" if "Platform" in df.columns else df.columns[2]
    url_col = "ProfileURL" if "ProfileURL" in df.columns else df.columns[0]

    # Filter strictly for TikTok rows (Column C == TikTok or URL contains tiktok.com)
    tiktok_mask = (
        df[platform_col].astype(str).str.strip().str.lower().isin(["tiktok", "tt"]) |
        df[url_col].astype(str).str.contains("tiktok.com", case=False, na=False)
    )

    tiktok_rows = df[tiktok_mask].copy()
    print(f"[+] Found {len(tiktok_rows)} TikTok profiles to scrape.\n")

    if tiktok_rows.empty:
        print("[!] No TikTok profiles found to process.")
        return

    updated_rows = []

    # Launch Headless Chromium
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        for idx, (original_index, row) in enumerate(tiktok_rows.iterrows(), 1):
            url = str(row[url_col]).strip()
            print(f"[{idx}/{len(tiktok_rows)}] Scraping TikTok: {url}")

            scraped_data = scrape_tiktok_profile(page, url)

            row_dict = row.to_dict()
            row_dict["Platform"] = "TikTok"

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
    print(f"\n[✓] Completed! Saved {len(final_df)} TikTok records to '{OUTPUT_CSV_FILE}'.")

if __name__ == "__main__":
    main()