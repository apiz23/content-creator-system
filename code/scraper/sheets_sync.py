"""Optional Google Sheets sync module.

Pushes newly-merged CRM rows to a Google Sheet tab after merge_to_crm()
succeeds. Supports both Service Account and OAuth2 installed app credentials.
Fails gracefully — never blocks the scrape if credentials are missing or
the API call errors out.

Auth methods:
- Service Account JSON: GOOGLE_SHEETS_CREDENTIALS_PATH points to JSON with
  "type": "service_account" (best for cron/CLI, no user interaction)
- OAuth2 Installed App: GOOGLE_SHEETS_CREDENTIALS_PATH points to JSON with
  "installed": {...} (requires one-time browser auth, token cached locally)
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROJECT_ROOT

# --- Lazy imports ---
try:
    import gspread
    _GS_AVAILABLE = True
except ImportError:
    _GS_AVAILABLE = False

try:
    from google.oauth2.service_account import Credentials as GSCredentials
    _has_sa = True
except ImportError:
    _has_sa = False

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials as OAuthCredentials
    _has_oauth = True
except ImportError:
    _has_oauth = False

TOKEN_FILE = PROJECT_ROOT / "data" / "oauth_token.json"

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
    """Load credentials from the JSON file path.

    Supports both Service Account and OAuth2 installed app credentials.
    Returns gspread-compatible Credentials object or None.
    """
    if not _GS_AVAILABLE:
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
        with open(creds_path) as f:
            cred_data = json.load(f)
    except Exception as e:
        print(f"[Sheets Sync] Failed to read credentials: {e}")
        return None

    # Determine credential type
    if "type" in cred_data and cred_data["type"] == "service_account":
        # Service Account — no user interaction needed
        if not _has_sa:
            print("[Sheets Sync] google-auth not installed for Service Account — skipping sync")
            return None
        try:
            creds = GSCredentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            return creds
        except Exception as e:
            print(f"[Sheets Sync] Service Account auth failed: {e}")
            return None

    elif "installed" in cred_data:
        # OAuth2 Installed App — needs browser flow once, then cached token
        if not _has_oauth:
            print("[Sheets Sync] google-auth-oauthlib not installed — skipping sync")
            return None

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]

        # Try to load cached token first
        creds = None
        if TOKEN_FILE.exists():
            try:
                token_data = json.loads(TOKEN_FILE.read_text())
                # Parse expiry string back to datetime
                expiry_str = token_data.get("expiry", "")
                expiry_dt = None
                if expiry_str:
                    try:
                        expiry_dt = datetime.fromisoformat(expiry_str)
                    except (ValueError, TypeError):
                        pass
                creds = OAuthCredentials(
                    token=token_data.get("token", ""),
                    refresh_token=token_data.get("refresh_token", ""),
                    expiry=expiry_dt
                )
                # Check if token is still valid
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Save refreshed token
                    TOKEN_FILE.write_text(json.dumps({
                        "token": creds.token,
                        "refresh_token": creds.refresh_token,
                        "expiry": creds.expiry.isoformat() if hasattr(creds, 'expiry') and creds.expiry else ""
                    }))
            except Exception:
                creds = None

        # If no valid cached token, run OAuth2 flow
        if creds is None or not creds.valid:
            print("[Sheets Sync] OAuth2 authentication required — opening browser...")
            print("[Sheets Sync] After login, the token will be cached for future runs.")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
            creds = flow.run_local_server(port=0)
            # Save token for next time
            TOKEN_FILE.write_text(json.dumps({
                "token": creds.token,
                "refresh_token": getattr(creds, 'refresh_token', ''),
                "expiry": getattr(creds, 'expiry', {}).isoformat() if hasattr(creds, 'expiry') else ""
            }))
            print("[Sheets Sync] OAuth2 authentication successful. Token cached.")

        return creds

    else:
        print("[Sheets Sync] Unknown credentials format — skipping sync")
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
