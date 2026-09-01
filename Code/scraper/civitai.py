import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
INPUT_CSV_FILE = "input_channels.csv"             # Input CSV with Civitai URLs
OUTPUT_CSV_FILE = "civitai_scraped_output.csv"   # Output updated CSV
API_BASE_URL = "https://civitai.com/api/v1"

# 1. Zero-Cost Local AI Classifier via Ollama
def classify_with_local_llm(bio: str, username: str, models_summary: str):
    prompt = f"""
    Analyze this Civitai AI creator/model developer profile:
    Username: {username}
    Bio: {bio}
    Top Models/Tags: {models_summary}

    Return ONLY a valid JSON object with these exact keys:
    {{
        "Tags": ["tag1", "tag2", "tag3"],
        "PrimaryAITool": "Name of primary model type or tool (e.g. Stable Diffusion, SDXL, LoRA, ComfyUI, Midjourney) or null",
        "AIGCVerdict": "yes",
        "Language": "English",
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
        combined = f"{username} {bio} {models_summary}".lower()
        tool = "LoRA" if "lora" in combined else ("Checkpoint" if "checkpoint" in combined else "Stable Diffusion")
        return {
            "Tags": ["Civitai", "AIGC", "Model Creator"],
            "PrimaryAITool": tool,
            "AIGCVerdict": "yes",
            "Language": "English",
            "Evidence": "Rule-based fallback for Civitai creator"
        }

def extract_email(text: str):
    if not text:
        return "not exposed"
    match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(text))
    return match.group(0) if match else "not exposed"

def extract_civitai_username(raw_url: str):
    if not isinstance(raw_url, str) or not raw_url.strip():
        return None
    match = re.search(r'civitai\.com/user/([a-zA-Z0-9_\-\.]+)', raw_url)
    if match:
        return match.group(1)
    # Fallback to last path segment if formatted differently
    clean_path = raw_url.strip("/").split("/")
    return clean_path[-1] if clean_path else None

# 2. Fetch Creator Data via Civitai Official API
def fetch_civitai_creator(username: str):
    try:
        # Query creators endpoint
        url = f"{API_BASE_URL}/creators?query={username}&limit=1"
        res = requests.get(url, timeout=15)
        if res.status_code != 200:
            return None
        
        data = res.json()
        items = data.get("items", [])
        
        # Match exact username if possible
        creator = None
        for item in items:
            if item.get("username", "").lower() == username.lower():
                creator = item
                break
        if not creator and items:
            creator = items[0] # Fallback to first search result

        if not creator:
            return None

        actual_username = creator.get("username", username)
        model_count = creator.get("modelCount", 0)

        # Fetch models by this creator to inspect types and tags
        models_url = f"{API_BASE_URL}/models?username={actual_username}&limit=5"
        m_res = requests.get(models_url, timeout=15)
        
        bio = ""
        sample_link = f"https://civitai.com/user/{actual_username}"
        model_tags = []
        
        if m_res.status_code == 200:
            m_data = m_res.json()
            m_items = m_data.get("items", [])
            for m in m_items:
                if m.get("description"):
                    bio += " " + re.sub('<[^<]+?>', '', m.get("description", ""))[:200] # strip HTML
                if m.get("tags"):
                    model_tags.extend(m.get("tags"))

        # Fallback tracking info
        unique_tags = list(set(model_tags))[:5]
        models_summary = ", ".join(unique_tags)
        
        ai_meta = classify_with_local_llm(bio, actual_username, models_summary)
        email = extract_email(bio)

        evidence = {
            "platform": "Civitai",
            "username": actual_username,
            "model_count": model_count,
            "top_tags": unique_tags,
            "aigc_verdict": "yes",
            "ai_reasoning": ai_meta.get("Evidence", "")
        }

        return {
            "Handle": f"@{actual_username}",
            "FollowerCount": "N/A", # Civitai API creators endpoint doesn't always expose exact followers directly, keep N/A or compute if available
            "Email": email,
            "Tags": ", ".join(ai_meta.get("Tags", [])) if isinstance(ai_meta.get("Tags"), list) else str(ai_meta.get("Tags")),
            "LastScrapedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Language": ai_meta.get("Language", "English"),
            "PrimaryAITool": ai_meta.get("PrimaryAITool", "Stable Diffusion"),
            "SampleContentURL": sample_link,
            "AIGCVerdict": "yes",
            "Notes": f"Civitai API: models={model_count}; tags={models_summary[:40]}",
            "FeedURL": f"https://civitai.com/user/{actual_username}/models",
            "ContactSourceURL": sample_link if email != "not exposed" else "",
            "EvidenceJSON": json.dumps(evidence)
        }

    except Exception as e:
        print(f"[-] Error querying Civitai API for {username}: {e}")
        return None

# --- 3. BATCH PROCESSOR ---
def main():
    if not os.path.exists(INPUT_CSV_FILE):
        print(f"[!] File '{INPUT_CSV_FILE}' not found.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = pd.read_csv(INPUT_CSV_FILE)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = [c.strip() for c in df.columns]

    platform_col = "Platform" if "Platform" in df.columns else df.columns[2]
    url_col = "ProfileURL" if "ProfileURL" in df.columns else df.columns[0]

    # Filter for Civitai rows
    civitai_mask = (
        df[platform_col].astype(str).str.strip().str.lower().isin(["civitai"]) |
        df[url_col].astype(str).str.contains("civitai.com", case=False, na=False)
    )

    civitai_rows = df[civitai_mask].copy()
    print(f"[+] Found {len(civitai_rows)} Civitai profiles to query via API.\n")

    if civitai_rows.empty:
        print("[!] No Civitai profiles found to process.")
        return

    updated_rows = []

    for idx, (original_index, row) in enumerate(civitai_rows.iterrows(), 1):
        url = str(row[url_col]).strip()
        username = extract_civitai_username(url)
        print(f"[{idx}/{len(civitai_rows)}] Querying Civitai user: {username or url}")

        scraped_data = fetch_civitai_creator(username) if username else None

        row_dict = row.to_dict()
        row_dict["Platform"] = "Civitai"

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
        time.sleep(1)  # Polite pacing for public API

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
    print(f"\n[✓] Completed! Saved {len(final_df)} Civitai records to '{OUTPUT_CSV_FILE}'.")

if __name__ == "__main__":
    main()