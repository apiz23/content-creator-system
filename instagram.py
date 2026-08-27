import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright

INPUT_CSV_FILE = "input_channels.csv"
OUTPUT_CSV_FILE = "instagram_scraped_output.csv"

def classify_with_local_llm(bio: str, handle: str):
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
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "format": "json", "stream": False},
            timeout=15
        )
        return json.loads(res.json().get("response", "{}"))
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

def extract_email(text: str):
    if not text:
        return "not exposed"
    match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(text))
    return match.group(0) if match else "not exposed"

def scrape_instagram_playwright(page, profile_url: str):
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2.5)

        # 1. Extract metadata from OpenGraph tags (Bypasses UI rate limits)
        og_desc = page.locator('meta[property="og:description"]').get_attribute("content") or ""
        
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
        ai_meta = classify_with_local_llm(bio, handle)
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

def main():
    df = pd.read_csv(INPUT_CSV_FILE)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = [c.strip() for c in df.columns]

    platform_col = "Platform" if "Platform" in df.columns else df.columns[2]
    url_col = "ProfileURL" if "ProfileURL" in df.columns else df.columns[0]

    ig_mask = (
        df[platform_col].astype(str).str.strip().str.lower().isin(["instagram", "ig"]) |
        df[url_col].astype(str).str.contains("instagram.com", case=False, na=False)
    )

    ig_rows = df[ig_mask].copy()
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

            scraped_data = scrape_instagram_playwright(page, url)
            row_dict = row.to_dict()
            row_dict["Platform"] = "Instagram"

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
            time.sleep(3)  # Wait 3 seconds between profiles

        browser.close()

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
    print(f"\n[✓] Completed! Saved to '{OUTPUT_CSV_FILE}'.")

if __name__ == "__main__":
    main()