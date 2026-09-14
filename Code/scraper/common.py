import re
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

INPUT_CSV_FILE = PROJECT_ROOT / "data/input/input_channels.csv"

CRM_FILE = PROJECT_ROOT / "data/Creator-Intel-CRM-List.csv"

BACKUP_DIR = PROJECT_ROOT / "data/backups"

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

def merge_to_crm(result_dict, crm_path=None):
    """Merge a single scraped result into the master CRM.

    Follows the safe-write procedure:
      1. Read current CRM, record row count
      2. Check if ProfileURL already exists
      3. Update if exists, append if new
      4. Validate, write, re-read to verify

    Returns (before_count, after_count, action: "updated"|"appended"|"skipped")
    """
    import pandas as pd

    if crm_path is None:
        crm_path = PROJECT_ROOT / "data" / "Creator-Intel-CRM-List.csv"

    crm_path = Path(crm_path)

    # Step 1: Read current CRM and record row count
    if not crm_path.exists():
        # Create CRM file with just this row
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
    Returns dict with before_count, after_count, updated, appended, skipped counts.
    """
    import pandas as pd

    if crm_path is None:
        crm_path = CRM_FILE

    before_count = len(pd.read_csv(crm_path)) if Path(crm_path).exists() else 0
    updated = 0
    appended = 0
    skipped = 0

    for _, row in results_df.iterrows():
        row_dict = row.to_dict()
        if any(v not in [None, "", "None"] for v in row_dict.values()):
            b, a, act = merge_to_crm(row_dict, crm_path)
            if act == "updated":
                updated += 1
            elif act == "appended":
                appended += 1
            else:
                skipped += 1

    after_count = len(pd.read_csv(crm_path)) if Path(crm_path).exists() else 0
    return {
        "before_count": before_count,
        "after_count": after_count,
        "updated": updated,
        "appended": appended,
        "skipped": skipped,
    }