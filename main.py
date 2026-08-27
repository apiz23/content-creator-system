import os
import re
import json
import requests
import pandas as pd
from datetime import datetime
import yt_dlp

# --- CONFIGURATION ---
INPUT_CSV_FILE = "input_channels.csv"           # Path to your input CSV
OUTPUT_CSV_FILE = "youtube_refreshed_output.csv" # Output updated CSV

# 1. Local AI Classifier via Ollama (llama3.2)
def classify_with_local_llm(bio: str, sample_text: str):
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
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "format": "json",
                "stream": False
            },
            timeout=15
        )
        return json.loads(res.json().get("response", "{}"))
    except Exception:
        # Smart fallback if Ollama is not active
        combined = f"{bio} {sample_text}".lower()
        tools = [t.title() for t in ["runway", "sora", "pika", "midjourney", "kling", "luma", "comfyui"] if t in combined]
        return {
            "Tags": ["AIGC", "YouTube", "AI-Creator"],
            "PrimaryAITool": tools[0] if tools else "GenAI",
            "AIGCVerdict": "yes" if any(k in combined for k in ["ai", "sora", "runway", "synthetic"]) else "no",
            "Language": "English",
            "Evidence": "Rule-based keyword extraction fallback"
        }

def extract_email(text: str):
    if not text:
        return "not exposed"
    match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    return match.group(0) if match else "not exposed"

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
                "FollowerCount": sub_count,
                "Email": email,
                "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
                "LastScrapedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Language": ai_meta.get("Language", "English"),
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
def main():
    if not os.path.exists(INPUT_CSV_FILE):
        print(f"[!] File '{INPUT_CSV_FILE}' not found. Please verify the filename.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    
    # Read CSV and drop any empty trailing unnamed columns
    df = pd.read_csv(INPUT_CSV_FILE)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # Normalize column names (strip leading/trailing whitespace)
    df.columns = [c.strip() for c in df.columns]

    print(f"[+] Total rows in CSV: {len(df)}")

    # Filter for YouTube: Column C ('Platform') is 'YouTube' or URL contains 'youtube.com'
    platform_col = "Platform" if "Platform" in df.columns else df.columns[2]
    url_col = "ProfileURL" if "ProfileURL" in df.columns else df.columns[0]

    youtube_mask = (
        df[platform_col].astype(str).str.strip().str.lower().isin(["youtube", "yt"]) |
        df[url_col].astype(str).str.contains("youtube.com", case=False, na=False)
    )

    yt_rows = df[youtube_mask].copy()
    print(f"[+] Identified {len(yt_rows)} YouTube channel rows to scrape.\n")

    updated_rows = []
    for idx, (original_index, row) in enumerate(yt_rows.iterrows(), 1):
        url = str(row[url_col]).strip()
        print(f"[{idx}/{len(yt_rows)}] Scraping YouTube profile: {url}")
        
        scraped_data = scrape_youtube_channel(url)
        
        row_dict = row.to_dict()
        row_dict["Platform"] = "YouTube"  # Ensure Column C is populated with YouTube
        
        if scraped_data:
            # Update fields with fresh scraped data
            row_dict["FollowerCount"] = scraped_data["FollowerCount"]
            if row_dict.get("Email") in [None, "", "not exposed"]:
                row_dict["Email"] = scraped_data["Email"]
            row_dict["LastScrapedAt"] = scraped_data["LastScrapedAt"]
            row_dict["PrimaryAITool"] = scraped_data["PrimaryAITool"] or row_dict.get("PrimaryAITool")
            row_dict["SampleContentURL"] = scraped_data["SampleContentURL"] or row_dict.get("SampleContentURL")
            row_dict["AIGCVerdict"] = scraped_data["AIGCVerdict"]
            row_dict["Notes"] = scraped_data["Notes"]
            row_dict["FeedURL"] = scraped_data["FeedURL"]
            row_dict["ContactSourceURL"] = scraped_data["ContactSourceURL"]
            row_dict["EvidenceJSON"] = scraped_data["EvidenceJSON"]
        
        updated_rows.append(row_dict)

    # Convert to DataFrame with exact column order
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
    print(f"\n[✓] Completed! Successfully scraped and saved YouTube records to '{OUTPUT_CSV_FILE}'.")

if __name__ == "__main__":
    main()