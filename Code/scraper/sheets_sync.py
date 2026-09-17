"""Optional Google Sheets sync module.

Pushes newly-merged CRM rows to a Google Sheet tab after merge_to_crm()
succeeds. Fully configured via .env. Fails gracefully — never blocks
the scrape if credentials are missing or the API call errors out.

Auth: Service Account JSON credentials (GOOGLE_SHEETS_CREDENTIALS_PATH).
A plain API key is read-only and CANNOT write to Sheets.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROJECT_ROOT

# Lazy import — only loaded if GOOGLE_SHEETS_ENABLED=true
try:
    import gspread
    from google.oauth2.service_account import Credentials as _GSCredentials
    _GS_AVAILABLE = True
except ImportError:
    _GS_AVAILABLE = False
    _GSCredentials = None

# --- Helpers ---

def _load_env():
    """Load .env variables if present."""
    from dotenv import load_dotenv
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)

def _is_enabled() -> bool:
    """Check if Google Sheets sync is enabled in .env."""
    _load_env()
    return os.getenv("GOOGLE_SHEETS_ENABLED", "false").strip().lower() == "true"

def _get_credentials():
    """Load service account credentials from the JSON file path.

    Returns gspread-compatible Credentials object or None if unavailable.
    """
    if not _GS_AVAILABLE or _GSCredentials is None:
        print("[Sheets Sync] gspread not installed — skipping sync")
        return None

    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "")
    if not creds_path:
        print("[Sheets Sync] GOOGLE_SHEETS_CREDENTIALS_PATH not set — skipping sync")
        return None

    if not Path(creds_path).exists():
        print(f"[Sheets Sync] Credentials file not found: {creds_path} — skipping sync")
        return None

    try:
        creds = _GSCredentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        return creds
    except Exception as e:
        print(f"[Sheets Sync] Failed to load credentials: {e} — skipping sync")
        return None

# --- Main sync function ---

def sync_to_sheet(rows: list, sheet_id: str = None, tab: str = None) -> dict:
    """Push newly-merged CRM rows to a Google Sheet.

    Args:
        rows: List of CRM row dicts (already validated/normalized by merge_to_crm).
        sheet_id: Override GOOGLE_SHEET_ID from .env.
        tab: Override GOOGLE_SHEET_TAB from .env.

    Returns:
        Dict with sync stats: {synced, skipped, errors, message}.
        Never raises — all errors are caught and logged.
    """
    _load_env()

    if not _is_enabled():
        return {"synced": 0, "skipped": len(rows), "errors": 0, "message": "Sync disabled"}

    if not rows:
        return {"synced": 0, "skipped": 0, "errors": 0, "message": "No rows to sync"}

    # Get config
    sheet_id = sheet_id or os.getenv("GOOGLE_SHEET_ID", "") or ""
    tab = tab or os.getenv("GOOGLE_SHEET_TAB", "CRM") or "CRM"

    if not sheet_id:
        return {"synced": 0, "skipped": len(rows), "errors": 1,
                "message": "GOOGLE_SHEET_ID not configured"}

    # Get credentials
    creds = _get_credentials()
    if creds is None:
        return {"synced": 0, "skipped": len(rows), "errors": 1,
                "message": "No valid credentials — skipping sync"}

    # Authenticate and open sheet
    try:
        client = gspread.authorize(creds)
    except Exception as e:
        print(f"[Sheets Sync] Failed to authorize: {e}")
        return {"synced": 0, "skipped": len(rows), "errors": 1,
                "message": f"Failed to authenticate: {e}"}

    try:
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(tab)
    except gspread.exceptions.SpreadsheetNotFound:
        return {"synced": 0, "skipped": len(rows), "errors": 1,
                "message": f"Spreadsheet {sheet_id} not found or access denied"}
    except gspread.exceptions.WorksheetNotFound:
        return {"synced": 0, "skipped": len(rows), "errors": 1,
                f"message": f"Tab '{tab}' not found in spreadsheet {sheet_id}"}
    except Exception as e:
        return {"synced": 0, "skipped": len(rows), "errors": 1,
                "message": f"Failed to open sheet: {e}"}

    # Get existing headers or fall back to TARGET_COLUMNS
    from common import TARGET_COLUMNS
    try:
        existing_values = worksheet.get_all_records()
        if existing_values:
            headers = list(existing_values[0].keys())
        else:
            headers = TARGET_COLUMNS
    except Exception:
        headers = TARGET_COLUMNS

    # Build set of existing ProfileURLs for dedup
    try:
        existing_row_values = worksheet.get_all_values()
        existing_urls = set()
        for row_vals in existing_row_values[1:]:
            if row_vals:
                existing_urls.add(row_vals[0])
    except Exception:
        existing_urls = set()

    # Sync rows
    sync_count = 0
    skip_count = 0
    error_count = 0

    for row in rows:
        profile_url = str(row.get("ProfileURL", ""))
        if profile_url in existing_urls:
            skip_count += 1
            continue

        try:
            row_values = [str(row.get(h, "")) for h in headers]
            worksheet.append_row(row_values, value_input_option="USER_ENTERED")
            sync_count += 1
        except Exception as row_err:
            error_count += 1
            print(f"[Sheets Sync] Error appending row {profile_url}: {row_err}")

    total = len(rows)
    message = f"Synced {sync_count}/{total} rows to {tab}"
    if skip_count > 0:
        message += f" ({skip_count} duplicates skipped)"
    if error_count > 0:
        message += f" ({error_count} errors)"

    return {
        "synced": sync_count,
        "skipped": skip_count,
        "errors": error_count,
        "message": message
    }


# --- Entry point for merge_to_crm integration ---

def sync_crm_to_sheet(rows: list) -> dict:
    """Convenience wrapper: sync rows to Google Sheets if enabled.

    Call this from merge_to_crm() or merge_results_to_crm() after
    a successful CRM merge + Data Quality Gate pass.

    Args:
        rows: List of dicts representing newly-merged/updated CRM rows.

    Returns:
        Dict with sync stats. Safe to call even if credentials missing.
    """
    if not _is_enabled():
        return {"synced": 0, "skipped": 0, "errors": 0, "message": "Sync disabled"}

    if not rows:
        return {"synced": 0, "skipped": 0, "errors": 0, "message": "No rows to sync"}

    return sync_to_sheet(rows)
