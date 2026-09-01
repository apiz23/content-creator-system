import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
INPUT_CSV_FILE = "input_channels.csv"           # Input CSV with Reddit URLs
OUTPUT_CSV_FILE = "reddit_scraped_output.csv"   # Output updated CSV

# 1. Zero-Cost Local AI Classifier via Ollama
def classify_with_local_llm(bio: str, sample_text: str, username: str):
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

def extract_email(text: str):
    if not text:
        return "not exposed"
    match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(text))
    return match.group(0) if match else "not exposed"

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
def scrape_reddit_profile_playwright(page, username: str):
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
        ai_meta = classify_with_local_llm(bio, sample_post_title, username)
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

    # Filter strictly for Reddit rows
    reddit_mask = (
        df[platform_col].astype(str).str.strip().str.lower().isin(["reddit", "rd"]) |
        df[url_col].astype(str).str.contains("reddit.com", case=False, na=False)
    )

    reddit_rows = df[reddit_mask].copy()
    print(f"[+] Found {len(reddit_rows)} Reddit profiles to scrape.\n")

    if reddit_rows.empty:
        print("[!] No Reddit profiles found to process.")
        return

    updated_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        for idx, (original_index, row) in enumerate(reddit_rows.iterrows(), 1):
            url = str(row[url_col]).strip()
            username = extract_reddit_username(url)

            if not username:
                print(f"[{idx}/{len(reddit_rows)}] Skipping invalid username: {url}")
                updated_rows.append(row.to_dict())
                continue

            print(f"[{idx}/{len(reddit_rows)}] Scraping Reddit: u/{username}")
            scraped_data = scrape_reddit_profile_playwright(page, username)

            row_dict = row.to_dict()
            row_dict["Platform"] = "Reddit"

            if scraped_data:
                row_dict["Name/Handle"] = scraped_data["Handle"]
                row_dict["FollowerCount"] = scraped_data["FollowerCount"]
                if row_dict.get("Email") in [None, "", "not exposed"]:
                    row_dict["Email"] = scraped_data["Email"]
                row_dict["LastScrapedAt"] = scraped_data["LastScrapedAt"]
                row_dict["Region"] = scraped_data["Region"] or row_dict.get("Region")
                row_dict["Language"] = scraped_data["Language"]
                row_dict["PrimaryAITool"] = scraped_data["PrimaryAITool"] or row_dict.get("PrimaryAITool")
                row_dict["SampleContentURL"] = scraped_data["SampleContentURL"] or row_dict.get("SampleContentURL")
                row_dict["AIGCVerdict"] = scraped_data["AIGCVerdict"]
                row_dict["Notes"] = scraped_data["Notes"]
                row_dict["FeedURL"] = scraped_data["FeedURL"]
                row_dict["ContactSourceURL"] = scraped_data["ContactSourceURL"]
                row_dict["EvidenceJSON"] = scraped_data["EvidenceJSON"]

            updated_rows.append(row_dict)
            time.sleep(1.5)  # Respect rate limits

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
    print(f"\n[✓] Completed! Saved {len(final_df)} Reddit records to '{OUTPUT_CSV_FILE}'.")

if __name__ == "__main__":
    main()