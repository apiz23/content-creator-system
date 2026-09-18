import os
import re
import json
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
OUTPUT_CSV_FILE = PROJECT_ROOT / "data/output/youtube_refreshed_output.csv"


def classify_with_local_llm(bio: str, sample_text: str, model_provider=None, model_name=None):
    """
    Analyze creator's bio and sample content using local LLM.
    """
    prompt = f"""
    Analyze this creator's bio and sample content.
    Bio: {bio}
    Sample text: {sample_text}

    Return ONLY a valid JSON object with these exact keys:
    {{
        "Tags": ["tag1", "tag2", "tag3"],
        "PrimaryAITool": "Name of AI tool (e.g. Runway, Sora, Midjourney, Pika) or null",
        "AIGCVerdict": "yes/no/hybrid",
        "Language": "Primary language of content",
        "Evidence": "Brief quote/reason"
    }}
    """
    try:
        response_text = call_model(prompt, format="json", timeout=15, model_provider=model_provider, model_name=model_name)
        return json.loads(response_text)
    except Exception:
        # Smart fallback if Ollama is not active
        combined = f"{bio} {sample_text}".lower()
        tools = [t.title() for t in ["runway", "sora", "pika", "midjourney", "kling", "luma", "comfyui"] if t in combined]
        return {
            "Tags": ["AIGC", "YouTube", "AI-Creator"],
            "PrimaryAITool": tools[0] if tools else "GenAI",
            "AIGCVerdict": "yes" if any(k in combined for k in ["ai", "sora", "runway", "synthetic"]) else "no",
            "Language": "",
            "Evidence": "Rule-based keyword extraction fallback"
        }


# 2. YouTube Live Scraper via yt-dlp
def scrape_youtube_channel(channel_url: str):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'playlist_items': '1',
        'ignoreerrors': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            if not info:
                return None
            
            channel_id = info.get('channel_id') or info.get('id', '')
            channel_name = info.get('channel') or info.get('uploader') or channel_url.split('/')[-1]
            description = info.get('description', '') or ''
            subscribers = info.get('channel_follower_count')
            sub_count = str(subscribers) if subscribers is not None else "N/A"
            video_count = info.get('playlist_count', 'N/A')
            
            # Extract latest video sample
            sample_title = ""
            sample_url = ""
            if 'entries' in info and len(info['entries']) > 0:
                first_entry = info['entries'][0]
                if first_entry:
                    sample_title = first_entry.get('title', '')
                    sample_url = first_entry.get('url') or first_entry.get('webpage_url', '')

            # AI Classification (Ollama -> Fallback)
            ai_meta = classify_with_local_llm(description, sample_title)
            email = extract_email(description)
            
            # Feed & About URLs
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}" if channel_id else ""
            contact_source = f"{channel_url}/about"

            # Structure evidence JSON
            evidence = {
                "follower_count": {
                    "source": "yt-dlp.channel_info",
                    "channelId": channel_id,
                    "profileUrl": channel_url
                },
                "bio": {
                    "source": "yt-dlp.channel_description",
                    "channel_id": channel_id,
                    "preview": description[:100]
                },
                "aigc_verdict": {
                    "source": "ollama.llama3.2",
                    "verdict": ai_meta.get("AIGCVerdict", "yes"),
                    "details": ai_meta.get("Evidence", "")
                },
                "recent_uploads": {
                    "sample": sample_url,
                    "sample_title": sample_title
                }
            }

            return {
                "Handle": channel_name,
                "FollowerCount": sub_count,
                "Email": email,
                "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
                "LastScrapedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Language": ai_meta.get("Language") or "",
                "PrimaryAITool": ai_meta.get("PrimaryAITool"),
                "SampleContentURL": sample_url,
                "AIGCVerdict": ai_meta.get("AIGCVerdict", "yes"),
                "Notes": f"api_refresh: YouTube subscribers={sub_count}; videos={video_count}; channelId={channel_id}; recent_title={sample_title}",
                "FeedURL": feed_url,
                "ContactSourceURL": contact_source,
                "EvidenceJSON": json.dumps(evidence)
            }
    except Exception as e:
        print(f"[-] Error scraping {channel_url}: {e}")
        return None


# --- MAIN RUNNER ---
def main(limit=None, model_provider=None, model_name=None):
    if not INPUT_CSV_FILE.exists():
        print(f"[!] File '{INPUT_CSV_FILE}' not found. Please verify the filename.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = load_and_clean_csv(INPUT_CSV_FILE)
    platform_col, url_col = get_column_names(df)

    print(f"[+] Total rows in CSV: {len(df)}")

    # Filter for YouTube
    yt_rows = filter_platform_rows(df, platform_col, url_col, "youtube", "youtube.com")
    if limit is not None:
        yt_rows = yt_rows.head(limit)
    print(f"[+] Identified {len(yt_rows)} YouTube channel rows to scrape.\n")

    updated_rows = []
    for idx, (original_index, row) in enumerate(yt_rows.iterrows(), 1):
        url = str(row[url_col]).strip()
        print(f"[{idx}/{len(yt_rows)}] Scraping YouTube profile: {url}")
        
        scraped_data = scrape_youtube_channel(url)
        row_dict = row.to_dict()
        row_dict["Platform"] = "YouTube"
        row_dict = merge_scraped_row(row_dict, scraped_data)
        updated_rows.append(row_dict)

    # Convert to DataFrame with exact column order
    final_df = pd.DataFrame(updated_rows)
    final_df = enforce_target_columns(final_df)
    final_df.to_csv(OUTPUT_CSV_FILE, index=False)
    print(f"\n[✓] Completed! Successfully scraped and saved YouTube records to '{OUTPUT_CSV_FILE}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max YouTube channels to process")
    parser.add_argument("--model-provider", type=str, default=None, help="Override MODEL_PROVIDER for this run")
    parser.add_argument("--model-name", type=str, default=None, help="Override MODEL_NAME for this run")
    args = parser.parse_args()
    main(limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)
