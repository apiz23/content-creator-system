import re
import shutil
import json
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

INPUT_CSV_FILE = PROJECT_ROOT / "data/input/input_channels.csv"

CRM_FILE = PROJECT_ROOT / "data/Creator-Intel-CRM-List.csv"

BACKUP_DIR = PROJECT_ROOT / "data/backups"
PENDING_REVIEW_FILE = PROJECT_ROOT / "data/pending_review.csv"

# Platform UI chrome tokens that may appear in bio/preview text across any platform
PLATFORM_UI_TOKENS = [
    r'\bLagi\b', r'\bSiaran\b', r'\bPerihal\b', r'\bReels\b',
    r'\bFoto\b', r'\bPengenalan\b', r'\bmengikuti\b', r'\bpengikut\b',
    r'\bRakan\b', r'\bPekerjaan\b', r'\btempat ker\b', r'\bTiada\b',
    r'\bMore\b', r'\bSee More\b', r'\bVer más\b', r'\bEn savoir plus\b',
    r'\bMeer lezen\b', r'\bVoir plus\b', r'\bCookie\b', r'\bcookie\b',
    r'\bAccept\b', r'\bAcceptance\b', r'\bConsent\b',
]

# Malay number suffixes: J = juta = million, K = ribu = thousand
MALAY_NUMBER_MAP = {'J': 'M', 'k': 'K'}

TARGET_COLUMNS = [
    "ProfileURL", "Name/Handle", "Platform", "FollowerCount", "Email",
    "Tags", "OutreachStatus", "LastScrapedAt", "Region", "Language",
    "PrimaryAITool", "SampleContentURL", "AIGCVerdict", "DiscoveredAt",
    "Source", "Notes", "FeedURL", "ContactSourceURL", "EvidenceJSON"
]

URL_PATTERNS = {
    "youtube": ["youtube.com", "youtu.be"],
    "vimeo": ["vimeo.com"],
    "civitai": ["civitai.com"],
    "threads": ["threads.net", "threads.com"],
    "tiktok": ["tiktok.com"],
    "instagram": ["instagram.com"],
    "facebook": ["facebook.com", "fb.com"],
    "linkedin": ["linkedin.com"],
    "reddit": ["reddit.com"],
}

PLATFORM_ALIASES = {
    "tt": "tiktok",
    "yt": "youtube",
    "vm": "vimeo",
    "ig": "instagram",
    "fb": "facebook",
    "li": "linkedin",
    "rd": "reddit",
    "thread": "threads",
}

def load_and_clean_csv(path):
    """Read CSV, drop unnamed columns, strip whitespace from column names."""
    import pandas as pd
    df = pd.read_csv(path)
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    df.columns = [c.strip() for c in df.columns]
    return df

def get_column_names(df):
    """Return (platform_col, url_col) with fallbacks for missing columns."""
    platform_col = "Platform" if "Platform" in df.columns else df.columns[2]
    url_col = "ProfileURL" if "ProfileURL" in df.columns else df.columns[0]
    return platform_col, url_col

def enforce_target_columns(df):
    """Add missing columns as None, reorder to canonical TARGET_COLUMNS order."""
    for col in TARGET_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[TARGET_COLUMNS]

def filter_platform_rows(df, platform_col, url_col, platform_name, domain):
    """Filter DataFrame rows matching a platform by name or domain."""
    mask = (
        df[platform_col].astype(str).str.strip().str.lower().isin([platform_name])
        & df[url_col].astype(str).str.contains(domain, case=False, na=False)
    )
    return df[mask].copy()

def detect_platform_from_url(url):
    """Detect platform name from URL domain. Returns platform key or None."""
    url_lower = url.lower()
    for platform, patterns in URL_PATTERNS.items():
        if any(p in url_lower for p in patterns):
            return platform
    return None

def extract_email(text):
    """Extract email address from text. Returns email or None."""
    if not text:
        return None
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", str(text))
    return match.group(0).lower() if match else None

def merge_scraped_row(row_dict, scraped_data):
    """Merge scraped data into an existing row dict, preserving existing values
    when scraped data is missing or empty."""
    if not scraped_data:
        return row_dict

    row_dict["Name/Handle"] = scraped_data.get("Handle") or row_dict.get("Name/Handle")
    row_dict["FollowerCount"] = scraped_data.get("FollowerCount") or row_dict.get("FollowerCount")

    if row_dict.get("Email") in [None, "", "not exposed"]:
        row_dict["Email"] = scraped_data.get("Email")

    row_dict["LastScrapedAt"] = scraped_data.get("LastScrapedAt")
    row_dict["Region"] = scraped_data.get("Region") or row_dict.get("Region")
    row_dict["Language"] = scraped_data.get("Language") or row_dict.get("Language")
    row_dict["PrimaryAITool"] = scraped_data.get("PrimaryAITool") or row_dict.get("PrimaryAITool")
    row_dict["SampleContentURL"] = scraped_data.get("SampleContentURL") or row_dict.get("SampleContentURL")
    row_dict["AIGCVerdict"] = scraped_data.get("AIGCVerdict")
    row_dict["Notes"] = scraped_data.get("Notes")
    row_dict["FeedURL"] = scraped_data.get("FeedURL")
    row_dict["ContactSourceURL"] = scraped_data.get("ContactSourceURL")
    row_dict["EvidenceJSON"] = scraped_data.get("EvidenceJSON")

    # Optional fields for scrapers that track detailed status
    for field in ["ScrapeStatus", "ScrapeError", "FollowerStatus", "EmailStatus",
                  "RegionStatus", "LanguageStatus", "AIToolStatus"]:
        if field in scraped_data:
            row_dict[field] = scraped_data[field]

    return row_dict


def route_to_pending_review(result_dict: dict, pending_path=None):
    """Write a discovery-only record to the pending-review queue file."""
    if pending_path is None:
        pending_path = PENDING_REVIEW_FILE
    pending_path = Path(pending_path)
    pending_path.parent.mkdir(parents=True, exist_ok=True)

    import pandas as pd
    row = {k: v for k, v in result_dict.items() if k in TARGET_COLUMNS}
    # Add metadata
    row.setdefault("OutreachStatus", "pending-review")
    row.setdefault("ScrapeStatus", "discovery-only")

    if pending_path.exists():
        df_existing = pd.read_csv(pending_path)
        # Check for duplicate
        profile_url = str(row.get("ProfileURL", "")).strip().lower()
        mask = df_existing["ProfileURL"].astype(str).str.strip().str.lower() == profile_url
        if mask.any():
            return  # Already in pending review
        df_new = pd.concat([df_existing, pd.DataFrame([row])], ignore_index=True)
    else:
        df_new = pd.DataFrame([row])

    df_new = enforce_target_columns(df_new)
    df_new.to_csv(pending_path, index=False)


def merge_to_crm(result_dict, crm_path=None):
    """Merge a single scraped result into the master CRM.

    Follows the safe-write procedure:
      1. Read current CRM, record row count
      2. Check if ProfileURL already exists
      3. Update if exists, append if new
      4. Validate, write, re-read to verify

    Discovery-only records (missing follower/bio data) are routed to
    a separate pending-review queue instead of the main CRM.

    Returns (before_count, after_count, action: "updated"|"appended"|"skipped"|"pending_review")
    """
    import pandas as pd

    if crm_path is None:
        crm_path = PROJECT_ROOT / "data" / "Creator-Intel-CRM-List.csv"

    crm_path = Path(crm_path)

    # Check if this is a discovery-only record
    if is_discovery_only(result_dict):
        route_to_pending_review(result_dict)
        return (0, 0, "pending_review")

    # Apply Output Formatting Standard to all scraped results
    result_dict = normalize_scraped_result(result_dict)

    # Step 1: Read current CRM and record row count
    if not crm_path.exists():
        result_df = pd.DataFrame([result_dict])
        result_df = enforce_target_columns(result_df)
        result_df.to_csv(crm_path, index=False)
        return (0, 1, "appended")

    before_count = len(pd.read_csv(crm_path))
    df = pd.read_csv(crm_path)

    # Ensure all TARGET_COLUMNS exist
    for col in TARGET_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Step 2: Check if ProfileURL already exists (case-insensitive, normalized)
    profile_url = str(result_dict.get("ProfileURL", "")).strip()
    profile_url_norm = profile_url.lower().strip().rstrip("/")
    existing_mask = df["ProfileURL"].astype(str).str.strip().str.lower().str.rstrip("/") == profile_url_norm

    if existing_mask.any():
        # Step 3a: Update existing row
        idx = existing_mask[existing_mask].index[0]
        existing_row = df.iloc[idx].to_dict()
        merged = merge_scraped_row(existing_row, result_dict)
        for key, value in merged.items():
            if key in df.columns:
                df.at[idx, key] = value
        action = "updated"
    else:
        # Step 3b: Append new row
        new_row = result_dict.copy()
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        action = "appended"

    # Step 4: Validate
    after_count = len(df)
    assert after_count >= before_count, "Row count decreased after merge!"
    for col in TARGET_COLUMNS:
        assert col in df.columns, f"Missing column {col} after merge!"

    # Step 5: Write
    df = df[TARGET_COLUMNS]
    df.to_csv(crm_path, index=False)

    # Step 6: Re-read to verify
    df_verify = pd.read_csv(crm_path)
    verify_count = len(df_verify)
    assert verify_count == after_count, f"Verification failed: wrote {after_count}, re-read {verify_count}"

    return (before_count, after_count, action)

def backup_crm(crm_path=None):
    """Create a timestamped backup of the Master CRM before modification.
    
    Returns the backup file path.
    Raises RuntimeError if backup creation fails.
    """
    if crm_path is None:
        crm_path = CRM_FILE
    
    crm_path = Path(crm_path)
    
    if not crm_path.exists():
        raise RuntimeError(f"CRM file not found: {crm_path}")
    
    # Ensure backup directory exists
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{crm_path.stem}_{timestamp}{crm_path.suffix}"
    backup_path = BACKUP_DIR / backup_name
    
    # Ensure we don't overwrite existing backup
    counter = 1
    while backup_path.exists():
        backup_name = f"{crm_path.stem}_{timestamp}_{counter}{crm_path.suffix}"
        backup_path = BACKUP_DIR / backup_name
        counter += 1
    
    # Copy CRM to backup
    try:
        shutil.copy2(crm_path, backup_path)
    except Exception as e:
        raise RuntimeError(f"Failed to create CRM backup: {e}")
    
    # Verify backup
    if not backup_path.exists():
        raise RuntimeError(f"Backup file not created: {backup_path}")
    
    return str(backup_path)


def merge_results_to_crm(results_df, crm_path=None):
    """Merge multiple scraped results (from a DataFrame) into the master CRM.

    Calls merge_to_crm for each row with a non-None result.
    Discovery-only records are routed to a pending-review queue.
    Returns dict with before_count, after_count, updated, appended, skipped, pending_review counts.
    """
    import pandas as pd

    if crm_path is None:
        crm_path = CRM_FILE

    before_count = len(pd.read_csv(crm_path)) if Path(crm_path).exists() else 0
    updated = 0
    appended = 0
    skipped = 0
    pending_review = 0

    for _, row in results_df.iterrows():
        row_dict = row.to_dict()
        if any(v not in [None, "", "None"] for v in row_dict.values()):
            b, a, act = merge_to_crm(row_dict, crm_path)
            if act == "updated":
                updated += 1
            elif act == "appended":
                appended += 1
            elif act == "pending_review":
                pending_review += 1
            else:
                skipped += 1

    after_count = len(pd.read_csv(crm_path)) if Path(crm_path).exists() else 0

    return {
        "before_count": before_count,
        "after_count": after_count,
        "updated": updated,
        "appended": appended,
        "skipped": skipped,
        "pending_review": pending_review,
    }


def create_english_context(browser, user_agent=None):
    """Create a browser context forced to English (en-US) locale.

    Sets Accept-Language header via extra_http_headers and locale
    to prevent UI text being returned in another language.
    Used by all Playwright-based platform scrapers.
    """
    if user_agent is None:
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    return browser.new_context(
        user_agent=user_agent,
        locale="en-US",
        viewport={"width": 1280, "height": 800},
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
        }
    )


def clean_platform_ui_text(text: str) -> str:
    """Strip platform UI chrome tokens from bio/preview text.

    Removes known menu labels, nav tabs, cookie banners, "more"/"see more"
    buttons, and similar fragments from any platform's bio text.
    Collapses whitespace/newlines into a single trimmed line.
    """
    if not text:
        return ""
    cleaned = text
    for token in PLATFORM_UI_TOKENS:
        cleaned = re.sub(token, ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def normalize_follower_to_kmb(raw: str) -> tuple:
    """Normalize locale-specific follower strings to standard K/M/B notation.

    Returns (normalized_string, raw_locale_string_for_evidence).
    Handles Malay "J" (juta=million), "pengikut" labels, and plain numbers.
    """
    raw = raw.strip()
    raw_locale = raw

    # Strip common labels
    count_str = re.sub(r'\s*(?:pengikut|mengikuti|men\s*ikut|followers?|likes?)\s*$', '', raw, flags=re.IGNORECASE).strip()

    # Handle Malay "J" (juta = million) suffix → convert to "M"
    count_str = re.sub(r'([\d.,]+)\s*J\b', r'\1M', count_str, flags=re.IGNORECASE)

    # Extract numeric part with optional suffix
    num_match = re.search(r'([\d.,]+)\s*([KkMmBb]?)', count_str)
    if num_match:
        number = num_match.group(1).replace(',', '')
        suffix = num_match.group(2).upper() if num_match.group(2) else ''
        try:
            val = float(number)
            if suffix == 'K':
                normalized = f"{val:g}K" if val < 1000 else f"{val/1000:g}M"
            elif suffix == 'M':
                normalized = f"{val:g}M" if val < 1000000 else f"{val/1000000:g}B"
            elif suffix == 'B':
                normalized = f"{val:g}B"
            else:
                # No suffix — auto-convert based on magnitude
                if val >= 1_000_000:
                    normalized = f"{val/1_000_000:g}M"
                elif val >= 1_000:
                    normalized = f"{val/1_000:g}K"
                else:
                    normalized = f"{val:g}"
        except ValueError:
            normalized = count_str
    else:
        normalized = count_str

    return normalized, raw_locale


def resolve_final_url(url: str) -> str:
    """Decode and extract the real target URL from double-wrapped strings.

    e.g. 'https://www.instagram.com/https%3A%2F%2Fwww.instagram.com%2Fhandle%2F'
    → 'https://www.instagram.com/handle/'
    """
    if not url:
        return ""
    # Try to decode URL-encoded nested URL
    decoded = unquote(url)
    # Check if decoded contains a nested URL pattern
    match = re.search(r'https?://.*?(https?://[^\s"\'<>]+)', decoded)
    if match and match.group(1) != decoded[:match.start()]:
        return match.group(1)
    # Check the original URL too
    match = re.search(r'https?://.*?(https?://[^\s"\'<>]+)', url)
    if match:
        return match.group(1)
    return url


def is_discovery_only(result_dict: dict) -> bool:
    """Check if a record is discovery-only (missing follower/bio data)."""
    status = str(result_dict.get("ScrapeStatus", result_dict.get("OutreachStatus", ""))).strip().lower()
    if status == "discovery-only":
        return True
    follower = str(result_dict.get("FollowerCount", "")).strip()
    bio_preview = str(result_dict.get("Notes", "")).strip()
    if not follower or follower in ("", "None", "N/A") or "discovery" in bio_preview.lower():
        return True
    return False

def normalize_scraped_result(result_dict: dict) -> dict:
    """Apply all Output Formatting Standard rules to a scraped result dict.

    Called by merge_to_crm() before any merge, so ALL scrapers
    automatically get formatted output regardless of platform.
    """
    # 1. Normalize FollowerCount to K/M/B notation
    raw_follower = str(result_dict.get("FollowerCount", "")).strip()
    if raw_follower and raw_follower not in ("None", "N/A", "", "nan"):
        normalized, raw_locale = normalize_follower_to_kmb(raw_follower)
        result_dict["FollowerCount"] = normalized
        try:
            evidence = json.loads(str(result_dict.get("EvidenceJSON", "{}")))
            if isinstance(evidence, dict):
                evidence["follower_raw_locale"] = raw_locale
                result_dict["EvidenceJSON"] = json.dumps(evidence)
        except (json.JSONDecodeError, TypeError):
            pass

    # 2. Clean Notes / bio_preview of platform UI chrome
    notes = result_dict.get("Notes", "")
    if notes and notes != "None":
        result_dict["Notes"] = clean_platform_ui_text(str(notes))

    # 3. Clean bio_preview inside EvidenceJSON
    try:
        evidence = json.loads(str(result_dict.get("EvidenceJSON", "{}")))
        if isinstance(evidence, dict):
            if "bio_preview" in evidence:
                evidence["bio_preview"] = clean_platform_ui_text(str(evidence["bio_preview"]))
            if "title" in evidence:
                evidence["title"] = clean_platform_ui_text(str(evidence["title"]))
            result_dict["EvidenceJSON"] = json.dumps(evidence)
    except (json.JSONDecodeError, TypeError):
        pass

    # 4. Resolve external links
    for url_field in ["SampleContentURL", "ContactSourceURL", "FeedURL"]:
        url_val = result_dict.get(url_field, "")
        if url_val and url_val != "None":
            resolved = resolve_final_url(str(url_val))
            result_dict[url_field] = resolved

    # 5. Clean Name/Handle of any UI tokens
    name = result_dict.get("Name/Handle", "")
    if name and name != "None":
        result_dict["Name/Handle"] = clean_platform_ui_text(str(name))

    return result_dict
