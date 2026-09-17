import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime
import yt_dlp
from pathlib import Path
import argparse

from model_client import call_model
from common import (
    PROJECT_ROOT, INPUT_CSV_FILE, TARGET_COLUMNS,
    load_and_clean_csv, get_column_names, enforce_target_columns,
    merge_scraped_row, extract_email, filter_platform_rows
)

# --- CONFIGURATION ---
OUTPUT_CSV_FILE = PROJECT_ROOT / "data/output/vimeo_scraped_output.csv"


def classify_with_local_llm(bio: str, sample_text: str, username: str, model_provider=None, model_name=None):
    """
    Analyze Vimeo filmmaker/creator's profile and video sample using local LLM.
    """
    prompt = f"""
    Analyze this Vimeo filmmaker/creator's profile and video sample:
    Username: {username}
    Bio/Description: {bio}
    Sample Video/Project: {sample_text}

    Return ONLY a valid JSON object with these exact keys:
    {{
        "Tags": ["tag1", "tag2", "tag3"],
        "PrimaryAITool": "Name of AI tool (e.g. Runway, Sora, Midjourney, Kling, ComfyUI, Pika) or null",
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
        tools = [t.title() for t in ["runway", "sora", "pika", "midjourney", "kling", "luma", "comfyui", "stable diffusion"] if t in combined]
        return {
            "Tags": ["Vimeo", "Filmmaker", "AIGC"],
            "PrimaryAITool": tools[0] if tools else "GenAI",
            "AIGCVerdict": "yes" if any(k in combined for k in ["ai film", "ai video", "synthetic", "generative", "diffusion"]) else "hybrid",
            "Language": "English",
            "Region": "Global",
            "Evidence": "Rule-based keyword fallback"
        }


def extract_vimeo_handle(raw_url: str):
    if not isinstance(raw_url, str) or not raw_url.strip():
        return None
    url = raw_url.strip()
    match = re.search(r'vimeo\.com/(?:channels/|user/)?([a-zA-Z0-9_\-]+)', url)
    if match:
        return f"@{match.group(1)}"
    return f"@{url.split('/')[-1]}"


# 2. Vimeo Profile & Video Scraper via yt-dlp & OpenGraph
def scrape_vimeo_profile(channel_url: str, model_provider=None, model_name=None):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'playlist_items': '1',
        'ignoreerrors': True
    }
    
    try:
        handle = extract_vimeo_handle(channel_url)
        description = ""
        uploader_name = handle.replace("@", "")
        follower_count = "N/A"
        sample_title = ""
        sample_url = channel_url
        video_count = 0

        # Method A: yt-dlp extraction
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if info:
                uploader_name = info.get('uploader') or info.get('channel') or uploader_name
                description = info.get('description') or ""
                entries = info.get('entries', [])
                video_count = len(entries) if entries else info.get('playlist_count', 0)
                
                if entries and entries[0]:
                    sample_title = entries[0].get('title', '')
                    sample_url = entries[0].get('url') or entries[0].get('webpage_url', channel_url)

        # Method B: Fallback metadata extraction via requests (OpenGraph tags)
        if not description or not sample_title:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
                res = requests.get(channel_url, headers=headers, timeout=10)
                if res.status_code == 200:
                    og_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', res.text)
                    if og_desc and not description:
                        description = og_desc.group(1)
                    
                    og_title = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', res.text)
                    if og_title and not sample_title:
                        sample_title = og_title.group(1)
            except Exception:
                pass

        follower_metric = f"{video_count} videos" if video_count else "N/A"

        # AI Classification & Contact Extraction
        ai_meta = classify_with_local_llm(description, sample_title, uploader_name, model_provider=model_provider, model_name=model_name)
        email = extract_email(description)

        evidence = {
            "platform": "Vimeo",
            "handle": handle,
            "uploader": uploader_name,
            "sample_title": sample_title,
            "bio_preview": description[:120],
            "aigc_verdict": ai_meta.get("AIGCVerdict", "hybrid"),
            "ai_reasoning": ai_meta.get("Evidence", "")
        }

        return {
            "Handle": handle,
            "FollowerCount": follower_metric,
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Region": ai_meta.get("Region") or "Global",
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool"),
            "SampleContentURL": sample_url,
            "AIGCVerdict": ai_meta.get("AIGCVerdict", "hybrid"),
            "Notes": f"Vimeo scrape: uploader={uploader_name}; recent_title={sample_title[:50]}",
            "FeedURL": f"{channel_url}/videos/rss" if not channel_url.endswith("/") else f"{channel_url}videos/rss",
            "ContactSourceURL": channel_url if email != "not exposed" else "",
            "EvidenceJSON": json.dumps(evidence)
        }

    except Exception as e:
        print(f"[-] Error scraping Vimeo URL {channel_url}: {e}")
        return None


# --- 3. BATCH PROCESSOR ---
def main(limit=None, model_provider=None, model_name=None):
    if not INPUT_CSV_FILE.exists():
        print(f"[!] File '{INPUT_CSV_FILE}' not found. Please create it or verify the path.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = load_and_clean_csv(INPUT_CSV_FILE)
    platform_col, url_col = get_column_names(df)

    # Filter strictly for Vimeo rows
    vimeo_rows = filter_platform_rows(df, platform_col, url_col, "vimeo", "vimeo.com")
    if limit is not None:
        vimeo_rows = vimeo_rows.head(limit)
    print(f"[+] Found {len(vimeo_rows)} Vimeo profiles/channels to scrape.\n")

    if vimeo_rows.empty:
        print("[!] No Vimeo profiles found to process.")
        return

    updated_rows = []
    for idx, (original_index, row) in enumerate(vimeo_rows.iterrows(), 1):
        url = str(row[url_col]).strip()
        print(f"[{idx}/{len(vimeo_rows)}] Scraping Vimeo: {url}")

        scraped_data = scrape_vimeo_profile(url, model_provider=model_provider, model_name=model_name)
        row_dict = row.to_dict()
        row_dict["Platform"] = "Vimeo"
        row_dict = merge_scraped_row(row_dict, scraped_data)
        updated_rows.append(row_dict)
        time.sleep(1)

    # Save to CSV
    final_df = pd.DataFrame(updated_rows)
    final_df = enforce_target_columns(final_df)
    final_df.to_csv(OUTPUT_CSV_FILE, index=False)
    print(f"\n[✓] Completed! Saved {len(final_df)} Vimeo records to '{OUTPUT_CSV_FILE}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max Vimeo profiles to process")
    parser.add_argument("--model-provider", type=str, default=None, help="Override MODEL_PROVIDER for this run")
    parser.add_argument("--model-name", type=str, default=None, help="Override MODEL_NAME for this run")
    args = parser.parse_args()
    main(limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)
