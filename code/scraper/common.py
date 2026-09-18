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

    def is_val_empty(val):
        """Check if a value is truly empty/unavailable."""
        if val is None:
            return True
        s = str(val).strip()
        return s in ("", "None", "N/A", "nan", "NaN")

    row_dict["Name/Handle"] = scraped_data.get("Handle") or row_dict.get("Name/Handle")

    # FollowerCount: treat "N/A" as unavailable, preserve existing valid value
    new_follower = scraped_data.get("FollowerCount")
    if not is_val_empty(new_follower):
        row_dict["FollowerCount"] = new_follower
    # else: preserve existing valid FollowerCount if any

    if row_dict.get("Email") in [None, "", "not exposed"]:
        email = scraped_data.get("Email")
        if not is_val_empty(email):
            row_dict["Email"] = email

    row_dict["LastScrapedAt"] = scraped_data.get("LastScrapedAt")

    # Region: only update if scraped_data has a valid value
    new_region = scraped_data.get("Region")
    if not is_val_empty(new_region):
        row_dict["Region"] = new_region

    # Language: only update if scraped_data has a valid, non-empty language
    new_language = scraped_data.get("Language")
    if not is_val_empty(new_language):
        row_dict["Language"] = new_language
    # else: preserve existing Language if any

    row_dict["PrimaryAITool"] = scraped_data.get("PrimaryAITool") or row_dict.get("PrimaryAITool")
    row_dict["SampleContentURL"] = scraped_data.get("SampleContentURL") or row_dict.get("SampleContentURL")
    row_dict["AIGCVerdict"] = scraped_data.get("AIGCVerdict")
    row_dict["Notes"] = scraped_data.get("Notes")

    # Tags: map from scraped_data if available, otherwise preserve existing
    new_tags = scraped_data.get("Tags")
    if not is_val_empty(new_tags):
        row_dict["Tags"] = new_tags

    # OutreachStatus: default to "New" for new records, preserve existing for known statuses
    if is_val_empty(row_dict.get("OutreachStatus")):
        row_dict["OutreachStatus"] = scraped_data.get("OutreachStatus") or "New"
    # else: preserve existing human-maintained outreach status

    # Source: use scraped source if available, otherwise preserve existing
    new_source = scraped_data.get("Source")
    if not is_val_empty(new_source):
        row_dict["Source"] = new_source

    # DiscoveredAt: only set for new records (existing row has empty DiscoveredAt)
    # If row already has a DiscoveredAt, never overwrite it
    if is_val_empty(row_dict.get("DiscoveredAt")):
        discovered = scraped_data.get("DiscoveredAt")
        if not is_val_empty(discovered):
            row_dict["DiscoveredAt"] = discovered

    # FeedURL: preserve existing if new value is empty
    new_feed = scraped_data.get("FeedURL")
    if not is_val_empty(new_feed):
        row_dict["FeedURL"] = new_feed
    # else: preserve existing FeedURL if any

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
    # Treat "N/A" as unavailable data, not necessarily discovery-only
    if not follower or follower in ("", "None", "nan", "NaN") or "discovery" in bio_preview.lower():
        return True
    return False


def _now_utc() -> str:
    """Return current UTC timestamp in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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


# =============================================================================
# SafeEnricher — Field-level safe enrichment for re-scraping
# =============================================================================

class SafeEnricher:
    """Enriches existing CRM records with scraped data without overwriting
    human-maintained fields.

    Core principle: NEVER LOSE DATA. Re-scraping is additive/enrichment only.

    For every field:
    - IF existing is empty AND new is valid/non-empty → fill it
    - IF existing is populated AND new is valid → update only per field rules
    - IF existing is populated AND new is empty/null → KEEP existing
    - NEVER replace existing data with empty/null/None/NaN/"N/A"
    """

    # Fields that are NEVER overwritten during re-scraping
    IMMUTABLE_FIELDS = {"ProfileURL", "DiscoveredAt", "Source", "OutreachStatus"}

    # Fields that preserve existing values when new scraped value is empty/invalid
    PRESERVE_IF_EMPTY = {
        "Name/Handle", "Platform", "FollowerCount", "Email",
        "Tags", "Region", "Language", "PrimaryAITool",
        "SampleContentURL", "AIGCVerdict", "Notes", "FeedURL",
        "ContactSourceURL", "EvidenceJSON",
    }

    # Fields that SHOULD be updated on every successful scrape
    UPDATE_ON_SUCCESS = {"LastScrapedAt"}

    # Fields where new valid value ENRICHES (merges with existing, not replaces)
    ENRICH_FIELDS = {"Tags"}

    @staticmethod
    def is_val_empty(val) -> bool:
        """Check if a value is truly empty/unavailable (NaN-safe)."""
        if val is None:
            return True
        s = str(val).strip()
        return s in ("", "None", "N/A", "nan", "NaN", "null", "NULL")

    @staticmethod
    def _normalize_profile_url(url: str) -> str:
        """Normalize ProfileURL for comparison."""
        return str(url).strip().lower().rstrip("/")

    def enrich(self, existing_row: dict, scraped_data: dict, scrape_successful: bool = True) -> tuple[dict, list[dict]]:
        """Enrich an existing CRM record with scraped data.

        Args:
            existing_row: The current CRM row dict (19 columns).
            scraped_data: The new scraped data dict.
            scrape_successful: Whether the scrape succeeded.

        Returns:
            tuple of (enriched_row_dict, change_report_list)
            change_report_list contains dicts with:
                field, old_value, new_value, status ("changed"|"unchanged"|"preserved")
        """
        enriched = existing_row.copy()
        changes = []

        # Track old values for comparison
        old_values = {k: v for k, v in enriched.items()}

        if not scraped_data:
            # No scraped data — keep everything as-is
            # Still report no changes
            for field in self.IMMUTABLE_FIELDS | self.PRESERVE_IF_EMPTY | self.UPDATE_ON_SUCCESS:
                if field in enriched:
                    changes.append({
                        "field": field, "old_value": old_values.get(field),
                        "new_value": old_values.get(field), "status": "unchanged"
                    })
            return enriched, changes

        # ---- IMMUTABLE FIELDS: NEVER change ----
        # ProfileURL is the identity key — never change
        # DiscoveredAt is original discovery time — never change
        # Source is original discovery source — never change
        # OutreachStatus is human-maintained — never auto-change

        # ---- LASTSCRAPEDAT: Update on success only ----
        if scrape_successful:
            new_scraped_at = scraped_data.get("LastScrapedAt") or self._now_utc()
            if not self.is_val_empty(new_scraped_at):
                enriched["LastScrapedAt"] = new_scraped_at
                changes.append({
                    "field": "LastScrapedAt",
                    "old_value": old_values.get("LastScrapedAt"),
                    "new_value": new_scraped_at, "status": "changed"
                })
        else:
            changes.append({
                "field": "LastScrapedAt",
                "old_value": old_values.get("LastScrapedAt"),
                "new_value": old_values.get("LastScrapedAt"), "status": "unchanged"
            })

        # ---- FIELD-LEVEL ENRICHMENT ----
        # Name/Handle: fill if empty, update if valid
        self._enrich_name_handle(enriched, scraped_data, old_values, changes)

        # Platform: fill if missing
        self._enrich_platform(enriched, scraped_data, old_values, changes)

        # FollowerCount: update if valid (dynamic field)
        self._enrich_follower_count(enriched, scraped_data, old_values, changes)

        # Email: fill empty, never replace valid
        self._enrich_email(enriched, scraped_data, old_values, changes)

        # Tags: enrich (merge, dedup)
        self._enrich_tags(enriched, scraped_data, old_values, changes)

        # Region: update only if reliable
        self._enrich_region(enriched, scraped_data, old_values, changes)

        # Language: update only if reliable evidence
        self._enrich_language(enriched, scraped_data, old_values, changes)

        # PrimaryAITool: enrich if reliable
        self._enrich_ai_tool(enriched, scraped_data, old_values, changes)

        # SampleContentURL: update only if valid new URL
        self._enrich_sample_url(enriched, scraped_data, old_values, changes)

        # FeedURL: update only if valid new URL
        self._enrich_feed_url(enriched, scraped_data, old_values, changes)

        # ContactSourceURL: update only if valid URL
        self._enrich_contact_url(enriched, scraped_data, old_values, changes)

        # AIGCVerdict: update only if new successful classification
        self._enrich_aigc_verdict(enriched, scraped_data, old_values, changes)

        # Notes: NEVER erase
        self._enrich_notes(enriched, scraped_data, old_values, changes)

        # EvidenceJSON: enrich if valid new evidence
        self._enrich_evidence_json(enriched, scraped_data, old_values, changes)

        # ---- Optional status fields from scrapers ----
        for field in ["ScrapeStatus", "ScrapeError", "FollowerStatus", "EmailStatus",
                       "RegionStatus", "LanguageStatus", "AIToolStatus"]:
            if field in scraped_data:
                enriched[field] = scraped_data[field]
                changes.append({
                    "field": field,
                    "old_value": old_values.get(field),
                    "new_value": scraped_data[field], "status": "changed"
                })

        # Report unchanged fields
        for field in self.IMMUTABLE_FIELDS:
            if field in enriched:
                changes.append({
                    "field": field,
                    "old_value": old_values.get(field),
                    "new_value": old_values.get(field), "status": "preserved"
                })

        return enriched, changes

    def _enrich_name_handle(self, enriched, scraped, old, changes):
        new_val = scraped.get("Handle") or scraped.get("Name/Handle")
        if not self.is_val_empty(new_val):
            if self.is_val_empty(old.get("Name/Handle")):
                enriched["Name/Handle"] = new_val
                changes.append({"field": "Name/Handle", "old_value": old.get("Name/Handle"),
                                "new_value": new_val, "status": "changed"})
            elif str(old.get("Name/Handle", "")).strip() != str(new_val).strip():
                # Only update if different — otherwise preserve
                enriched["Name/Handle"] = new_val
                changes.append({"field": "Name/Handle", "old_value": old.get("Name/Handle"),
                                "new_value": new_val, "status": "changed"})

    def _enrich_platform(self, enriched, scraped, old, changes):
        new_val = scraped.get("Platform")
        if not self.is_val_empty(new_val) and self.is_val_empty(old.get("Platform")):
            enriched["Platform"] = new_val
            changes.append({"field": "Platform", "old_value": old.get("Platform"),
                            "new_value": new_val, "status": "changed"})

    def _enrich_follower_count(self, enriched, scraped, old, changes):
        new_val = scraped.get("FollowerCount")
        if not self.is_val_empty(new_val):
            enriched["FollowerCount"] = new_val
            changes.append({"field": "FollowerCount", "old_value": old.get("FollowerCount"),
                            "new_value": new_val, "status": "changed"})

    def _enrich_email(self, enriched, scraped, old, changes):
        new_val = scraped.get("Email")
        if not self.is_val_empty(new_val) and self.is_val_empty(old.get("Email")):
            enriched["Email"] = new_val
            changes.append({"field": "Email", "old_value": old.get("Email"),
                            "new_value": new_val, "status": "changed"})

    def _enrich_tags(self, enriched, scraped, old, changes):
        new_tags = scraped.get("Tags")
        if not self.is_val_empty(new_tags):
            existing_tags = str(old.get("Tags", "")).strip()
            if self.is_val_empty(existing_tags):
                enriched["Tags"] = new_tags
                changes.append({"field": "Tags", "old_value": old.get("Tags"),
                                "new_value": new_tags, "status": "changed"})
            else:
                # Merge: split both, dedup, rejoin
                existing_set = set(t.strip() for t in existing_tags.split(",") if t.strip())
                new_set = set(t.strip() for t in str(new_tags).split(",") if t.strip())
                merged = existing_set | new_set
                merged_str = ", ".join(sorted(merged))
                if merged_str != existing_tags:
                    enriched["Tags"] = merged_str
                    changes.append({"field": "Tags", "old_value": old.get("Tags"),
                                    "new_value": merged_str, "status": "changed"})

    def _enrich_region(self, enriched, scraped, old, changes):
        new_val = scraped.get("Region")
        if not self.is_val_empty(new_val) and self.is_val_empty(old.get("Region")):
            enriched["Region"] = new_val
            changes.append({"field": "Region", "old_value": old.get("Region"),
                            "new_value": new_val, "status": "changed"})

    def _enrich_language(self, enriched, scraped, old, changes):
        new_val = scraped.get("Language")
        if not self.is_val_empty(new_val) and self.is_val_empty(old.get("Language")):
            enriched["Language"] = new_val
            changes.append({"field": "Language", "old_value": old.get("Language"),
                            "new_value": new_val, "status": "changed"})

    def _enrich_ai_tool(self, enriched, scraped, old, changes):
        new_val = scraped.get("PrimaryAITool")
        if not self.is_val_empty(new_val) and self.is_val_empty(old.get("PrimaryAITool")):
            enriched["PrimaryAITool"] = new_val
            changes.append({"field": "PrimaryAITool", "old_value": old.get("PrimaryAITool"),
                            "new_value": new_val, "status": "changed"})

    def _enrich_sample_url(self, enriched, scraped, old, changes):
        new_val = scraped.get("SampleContentURL")
        if not self.is_val_empty(new_val) and self.is_val_empty(old.get("SampleContentURL")):
            enriched["SampleContentURL"] = new_val
            changes.append({"field": "SampleContentURL", "old_value": old.get("SampleContentURL"),
                            "new_value": new_val, "status": "changed"})

    def _enrich_feed_url(self, enriched, scraped, old, changes):
        new_val = scraped.get("FeedURL")
        if not self.is_val_empty(new_val) and self.is_val_empty(old.get("FeedURL")):
            enriched["FeedURL"] = new_val
            changes.append({"field": "FeedURL", "old_value": old.get("FeedURL"),
                            "new_value": new_val, "status": "changed"})

    def _enrich_contact_url(self, enriched, scraped, old, changes):
        new_val = scraped.get("ContactSourceURL")
        if not self.is_val_empty(new_val) and self.is_val_empty(old.get("ContactSourceURL")):
            enriched["ContactSourceURL"] = new_val
            changes.append({"field": "ContactSourceURL", "old_value": old.get("ContactSourceURL"),
                            "new_value": new_val, "status": "changed"})

    def _enrich_aigc_verdict(self, enriched, scraped, old, changes):
        new_val = scraped.get("AIGCVerdict")
        if not self.is_val_empty(new_val) and self.is_val_empty(old.get("AIGCVerdict")):
            enriched["AIGCVerdict"] = new_val
            changes.append({"field": "AIGCVerdict", "old_value": old.get("AIGCVerdict"),
                            "new_value": new_val, "status": "changed"})

    def _enrich_notes(self, enriched, scraped, old, changes):
        # Notes are NEVER erased by scraping — preserve human-written notes
        # Only fill if existing notes are completely empty
        new_notes = scraped.get("Notes")
        if not self.is_val_empty(new_notes) and self.is_val_empty(old.get("Notes")):
            enriched["Notes"] = new_notes
            changes.append({"field": "Notes", "old_value": old.get("Notes"),
                            "new_value": new_notes, "status": "changed"})

    def _enrich_evidence_json(self, enriched, scraped, old, changes):
        new_evidence = scraped.get("EvidenceJSON")
        if not self.is_val_empty(new_evidence):
            existing_evidence = str(old.get("EvidenceJSON", "")).strip()
            if self.is_val_empty(existing_evidence):
                enriched["EvidenceJSON"] = new_evidence
                changes.append({"field": "EvidenceJSON", "old_value": old.get("EvidenceJSON"),
                                "new_value": new_evidence, "status": "changed"})
            else:
                # Merge: try to combine evidence objects
                try:
                    existing_json = json.loads(existing_evidence) if existing_evidence else {}
                    new_json = json.loads(str(new_evidence))
                    if isinstance(existing_json, dict) and isinstance(new_json, dict):
                        merged = {**existing_json, **new_json}
                        merged_str = json.dumps(merged, ensure_ascii=False)
                        if merged_str != existing_evidence:
                            enriched["EvidenceJSON"] = merged_str
                            changes.append({"field": "EvidenceJSON", "old_value": old.get("EvidenceJSON"),
                                            "new_value": merged_str, "status": "changed"})
                except (json_mod.JSONDecodeError, TypeError):
                    pass  # Preserve existing valid JSON

    @staticmethod
    def _now_utc() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def is_discovery_only(result_dict: dict) -> bool:
        """Check if a record is discovery-only (missing follower/bio data)."""
        status = str(result_dict.get("ScrapeStatus", result_dict.get("OutreachStatus", ""))).strip().lower()
        if status == "discovery-only":
            return True
        follower = str(result_dict.get("FollowerCount", "")).strip()
        bio_preview = str(result_dict.get("Notes", "")).strip()
        if not follower or follower in ("", "None", "nan", "NaN") or "discovery" in bio_preview.lower():
            return True
        return False
