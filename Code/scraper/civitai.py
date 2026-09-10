import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import argparse

from model_client import call_model
from common import (
    PROJECT_ROOT, INPUT_CSV_FILE, TARGET_COLUMNS,
    load_and_clean_csv, get_column_names, enforce_target_columns,
    merge_scraped_row, extract_email, filter_platform_rows
)

# --- CONFIGURATION ---
OUTPUT_CSV_FILE = PROJECT_ROOT / "data/output/civitai_scraped_output.csv"
API_BASE_URL = "https://civitai.com/api/v1"


def classify_with_local_llm(bio: str, username: str, models_summary: str, model_provider=None, model_name=None):
    """
    Analyze Civitai AI creator/model developer profile using local LLM.
    """
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
        response_text = call_model(prompt, format="json", timeout=15, model_provider=model_provider, model_name=model_name)
        return json.loads(response_text)
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
def fetch_civitai_creator(username: str, model_provider=None, model_name=None):
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
        
        ai_meta = classify_with_local_llm(bio, actual_username, models_summary, model_provider=model_provider, model_name=model_name)
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
def main(limit=None, model_provider=None, model_name=None):
    if not INPUT_CSV_FILE.exists():
        print(f"[!] File '{INPUT_CSV_FILE}' not found.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = load_and_clean_csv(INPUT_CSV_FILE)
    platform_col, url_col = get_column_names(df)

    # Filter for Civitai rows
    civitai_rows = filter_platform_rows(df, platform_col, url_col, "civitai", "civitai.com")
    if limit is not None:
        civitai_rows = civitai_rows.head(limit)
    print(f"[+] Found {len(civitai_rows)} Civitai profiles to query via API.\n")

    if civitai_rows.empty:
        print("[!] No Civitai profiles found to process.")
        return

    updated_rows = []

    for idx, (original_index, row) in enumerate(civitai_rows.iterrows(), 1):
        url = str(row[url_col]).strip()
        username = extract_civitai_username(url)
        print(f"[{idx}/{len(civitai_rows)}] Querying Civitai user: {username or url}")

        scraped_data = fetch_civitai_creator(username, model_provider=model_provider, model_name=model_name) if username else None
        row_dict = row.to_dict()
        row_dict["Platform"] = "Civitai"
        row_dict = merge_scraped_row(row_dict, scraped_data)
        updated_rows.append(row_dict)
        time.sleep(1)  # Polite pacing for public API

    # Save to CSV
    final_df = pd.DataFrame(updated_rows)
    final_df = enforce_target_columns(final_df)
    final_df.to_csv(OUTPUT_CSV_FILE, index=False)
    print(f"\n[✓] Completed! Saved {len(final_df)} Civitai records to '{OUTPUT_CSV_FILE}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max Civitai profiles to process")
    parser.add_argument("--model-provider", type=str, default=None, help="Override MODEL_PROVIDER for this run")
    parser.add_argument("--model-name", type=str, default=None, help="Override MODEL_NAME for this run")
    args = parser.parse_args()
    main(limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)
