import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import unquote, urlparse, parse_qs, quote
from playwright.sync_api import sync_playwright
from pathlib import Path
import argparse

from model_client import call_model
from common import (
    PROJECT_ROOT, INPUT_CSV_FILE, TARGET_COLUMNS,
    load_and_clean_csv, get_column_names, enforce_target_columns,
    merge_scraped_row, extract_email, filter_platform_rows
)

# --- CONFIGURATION ---
OUTPUT_CSV_FILE = PROJECT_ROOT / "data/output/facebook_scraped_output.csv"

# Malay/Indonesian Facebook UI chrome tokens to strip from bio text
FACEBOOK_UI_TOKENS = [
    r'\bLagi\b', r'\bSiaran\b', r'\bPerihal\b', r'\bReels\b',
    r'\bFoto\b', r'\bPengenalan\b', r'\bmengikuti\b', r'\bpengikut\b',
    r'\bRakan\b', r'\bPekerjaan\b', r'\btempat ker\b', r'\bTiada\b',
    r'\bFoto\b', r'\bVideo\b', r'\bSiaran\b', r'\bPasar\b',
]

# Malay number suffixes: J = juta = million, K = ribu = thousand
MALAY_NUMBER_MAP = {
    'J': 'M',   # juta → million
    'k': 'K',   # ribu → thousand (already K but normalize)
}

# Clean Facebook UI pattern for notes
FB_UI_PATTERN = re.compile(
    r'\s*(?:Lagi|Siaran|Perihal|Reels|Foto|Pengenalan|mengikuti|pengikut|'
    r'Rakan|Pekerjaan|tempat ker|Tiada|Video|Pasar)\s*',
    re.IGNORECASE
)

# Double-wrapped URL detection (URL nested inside another URL param)
DOUBLE_WRAP_PATTERN = re.compile(r'https?://.*?(https?://[^\s"\'<>]+)')


def normalize_follower_count(raw: str) -> tuple:
    """Normalize locale-specific follower strings to standard K/M/B notation.

    Returns (normalized_string, raw_locale_string_for_evidence).
    - "1.2K pengikut" → ("1.2K", "1.2K pengikut")
    - "1.1J pengikut" → ("1.1M", "1.1J pengikut")
    - "1,108,428" → ("1.1M", "1,108,428")
    - "559K" → ("559K", "559K")
    """
    raw = raw.strip()
    raw_locale = raw  # preserve original for traceability

    # Strip Malay labels like "pengikut", "mengikuti" from the count string
    count_str = re.sub(r'\s*(?:pengikut|mengikuti|pengikut|men\s*ikut)\s*$', '', raw, flags=re.IGNORECASE).strip()

    # Handle Malay "J" (juta = million) suffix → convert to "M"
    count_str = re.sub(r'([\d.,]+)\s*J\b', r'\1M', count_str, flags=re.IGNORECASE)

    # Extract just the numeric part (e.g., "1.2K", "1.1M", "559K")
    num_match = re.search(r'([\d.,]+)\s*([KkMmBb]?)', count_str)
    if num_match:
        number = num_match.group(1).replace(',', '')
        suffix = num_match.group(2).upper() if num_match.group(2) else ''
        # If we have a number and a suffix, reconstruct
        try:
            val = float(number)
            if suffix == 'K':
                if val >= 1000:
                    normalized = f"{val/1000:.1f}M".rstrip('0').rstrip('.') + 'M'
                else:
                    normalized = f"{val:g}K"
            elif suffix == 'M':
                if val >= 1000:
                    normalized = f"{val/1000000:.1f}B".rstrip('0').rstrip('.') + 'B'
                else:
                    normalized = f"{val:g}M"
            elif suffix == 'B':
                normalized = f"{val:g}B"
            else:
                # No suffix but large number — auto-convert
                if val >= 1_000_000:
                    normalized = f"{val/1_000_000:.1f}M".rstrip('0').rstrip('.')
                elif val >= 1_000:
                    normalized = f"{val/1_000:.1f}K".rstrip('0').rstrip('.')
                else:
                    normalized = f"{val:,.0f}"
        except ValueError:
            normalized = count_str
    else:
        normalized = count_str

    return normalized, raw_locale


def clean_bio_preview(bio: str) -> str:
    """Strip Facebook Malay UI chrome tokens and collapse to single clean line.

    Removes tokens like 'Lagi', 'Siaran', 'Perihal', 'Reels', 'Foto', 'Pengenalan'
    and collapses whitespace/newlines into a single trimmed line.
    """
    if not bio:
        return ""
    cleaned = bio
    for token in FACEBOOK_UI_TOKENS:
        cleaned = re.sub(token, ' ', cleaned)
    # Collapse whitespace/newlines to single space, trim
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def normalize_external_link(url: str) -> str:
    """Decode and extract the real target URL from double-wrapped strings.

    e.g. 'https://www.instagram.com/https%3A%2F%2Fwww.instagram.com%2Fhandle%2F'
    → 'https://www.instagram.com/handle/'
    """
    if not url:
        return ""
    # Try to decode URL-encoded nested URL
    decoded = unquote(url)
    # Check if decoded contains a nested URL
    match = DOUBLE_WRAP_PATTERN.search(decoded)
    if match and match.group(1) != decoded[:match.start()]:
        return match.group(1)
    # Check the original URL too
    match = DOUBLE_WRAP_PATTERN.search(url)
    if match:
        return match.group(1)
    return url


def create_facebook_context(browser):
    """Create a browser context forced to English (en-US) locale.

    Sets Accept-Language header via extra_http_headers and locale
    to prevent Malay/Indonesian UI text.
    """
    return browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        locale="en-US",
        viewport={"width": 1280, "height": 800},
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
        }
    )


def classify_with_local_llm(bio: str, handle: str, model_provider=None, model_name=None):
    """
    Analyze Facebook page/creator's name and bio using local LLM.
    """
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
        response_text = call_model(prompt, format="json", timeout=15, model_provider=model_provider, model_name=model_name)
        return json.loads(response_text)
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
def scrape_facebook_profile(page, profile_url: str, model_provider=None, model_name=None):
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(2.5)

        handle = extract_facebook_username(profile_url)

        # 1. Extract OpenGraph Meta Tags (Most reliable without logging in)
        og_title = page.locator('meta[property="og:title"]').get_attribute("content") or ""
        og_desc = page.locator('meta[property="og:description"]').get_attribute("content") or ""
        
        # 2. Extract Followers / Likes (normalize to English K/M/B notation)
        follower_count_raw = "N/A"
        # Often in og:description: "X likes · Y talking about this" or "X followers"
        fol_match = re.search(r'([\d\.,]+[KkMmBbJj]?)\s*(?:followers|likes|pengikut|mengikuti)', og_desc, re.IGNORECASE)
        if fol_match:
            follower_count_raw = fol_match.group(1)
        else:
            # Try searching page text
            body_text = page.inner_text("body")
            fol_match_body = re.search(r'([\d\.,]+[KkMmBbJj]?)\s*followers', body_text, re.IGNORECASE)
            if fol_match_body:
                follower_count_raw = fol_match_body.group(1)

        # Normalize follower count to standard K/M/B notation
        follower_count, raw_locale_str = normalize_follower_count(follower_count_raw)

        # 3. Extract Bio / Intro (clean Malay UI chrome tokens)
        bio = og_desc
        try:
            intro_elem = page.locator('div[role="main"]').inner_text()
            if intro_elem and len(intro_elem) > len(bio):
                bio = intro_elem[:300]
        except Exception:
            pass
        # Clean bio preview: strip Malay UI tokens, collapse to single line
        bio_clean = clean_bio_preview(bio)

        # 4. Extract External Link (decode double-wrapped URLs)
        external_link = ""
        try:
            links = page.locator('a[href*="http"]').all()
            for l in links:
                href = l.get_attribute("href") or ""
                if "l.facebook.com" in href:
                    external_link = normalize_external_link(clean_facebook_url(href))
                    break
                elif not any(d in href for d in ["facebook.com", "fb.com", "instagram.com"]):
                    external_link = normalize_external_link(href)
                    break
        except Exception:
            pass

        # AI Classification & Email Discovery
        ai_meta = classify_with_local_llm(bio, handle or og_title, model_provider=model_provider, model_name=model_name)
        email = extract_email(bio)

        evidence = {
            "platform": "Facebook",
            "handle": handle,
            "title": og_title,
            "bio_preview": bio_clean[:100],
            "external_link": external_link,
            "aigc_verdict": ai_meta.get("AIGCVerdict", "yes"),
            "ai_reasoning": ai_meta.get("Evidence", ""),
            "follower_raw_locale": raw_locale_str
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
            "Notes": f"Facebook scrape: followers={follower_count}; bio_preview={bio_clean[:60].strip()}",
            "FeedURL": profile_url,
            "ContactSourceURL": profile_url if email != "not exposed" else external_link,
            "EvidenceJSON": json.dumps(evidence)
        }

    except Exception as e:
        print(f"[-] Error scraping Facebook {profile_url}: {e}")
        return None


# --- 3. BATCH PROCESSOR ---
def main(limit=None, model_provider=None, model_name=None):
    if not INPUT_CSV_FILE.exists():
        print(f"[!] File '{INPUT_CSV_FILE}' not found. Please create it or verify the path.")
        return

    print(f"[+] Loading input file: {INPUT_CSV_FILE}")
    df = load_and_clean_csv(INPUT_CSV_FILE)
    platform_col, url_col = get_column_names(df)

    # Filter strictly for Facebook rows
    fb_rows = filter_platform_rows(df, platform_col, url_col, "facebook", "facebook.com")
    if limit is not None:
        fb_rows = fb_rows.head(limit)
    print(f"[+] Found {len(fb_rows)} Facebook profiles to scrape.\n")

    if fb_rows.empty:
        print("[!] No Facebook profiles found to process.")
        return

    updated_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = create_facebook_context(browser)
        page = context.new_page()

        for idx, (original_index, row) in enumerate(fb_rows.iterrows(), 1):
            url = str(row[url_col]).strip()
            print(f"[{idx}/{len(fb_rows)}] Scraping Facebook: {url}")

            scraped_data = scrape_facebook_profile(page, url, model_provider=model_provider, model_name=model_name)
            row_dict = row.to_dict()
            row_dict["Platform"] = "Facebook"
            row_dict = merge_scraped_row(row_dict, scraped_data)
            updated_rows.append(row_dict)
            time.sleep(2)  # Wait 2s to avoid aggressive Facebook IP throttling

        browser.close()

    # Save to CSV
    final_df = pd.DataFrame(updated_rows)
    final_df = enforce_target_columns(final_df)
    final_df.to_csv(OUTPUT_CSV_FILE, index=False)
    print(f"\n[✓] Completed! Saved {len(final_df)} Facebook records to '{OUTPUT_CSV_FILE}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max Facebook profiles to process")
    parser.add_argument("--model-provider", type=str, default=None, help="Override MODEL_PROVIDER for this run")
    parser.add_argument("--model-name", type=str, default=None, help="Override MODEL_NAME for this run")
    args = parser.parse_args()
    main(limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)
