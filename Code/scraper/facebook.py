import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import unquote
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
INPUT_CSV_FILE = "input_channels.csv"             # Input CSV with Facebook URLs
OUTPUT_CSV_FILE = "facebook_scraped_output.csv"   # Output updated CSV

# 1. Zero-Cost Local AI Classifier via Ollama
def classify_with_local_llm(bio: str, handle: str):
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
        combined = f"{handle} {bio}".lower()
        tools = [t.title() for t in ["midjourney", "sora", "runway", "kling", "luma", "chatgpt", "claude", "stable diffusion"] if t in combined]
        return {
            "Tags": ["Facebook", "AIGC", "Creator"],
            "PrimaryAITool": tools[0] if tools else "GenAI",
            "AIGCVerdict": "yes" if any(k in combined for k in ["ai", "synthetic", "generative", "midjourney", "bot"]) else "hybrid",
            "Language": "English",
            "Evidence": "Rule-based keyword fallback"
        }

def extract_email(text: str):
    if not text:
        return "not exposed"
    match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(text))
    return match.group(0) if match else "not exposed"

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
def scrape_facebook_profile(page, profile_url: str):
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
        ai_meta = classify_with_local_llm(bio, handle or og_title)
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

    # Filter strictly for Facebook rows
    fb_mask = (
        df[platform_col].astype(str).str.strip().str.lower().isin(["facebook", "fb"]) |
        df[url_col].astype(str).str.contains("facebook.com", case=False, na=False)
    )

    fb_rows = df[fb_mask].copy()
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

            scraped_data = scrape_facebook_profile(page, url)

            row_dict = row.to_dict()
            row_dict["Platform"] = "Facebook"

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
            time.sleep(2)  # Wait 2s to avoid aggressive Facebook IP throttling

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
    print(f"\n[✓] Completed! Saved {len(final_df)} Facebook records to '{OUTPUT_CSV_FILE}'.")

if __name__ == "__main__":
    main()