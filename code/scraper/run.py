#!/usr/bin/env python3
"""
Unified scraper dispatcher with full-CSV batch dispatch.

Usage:
    python3 code/scraper/run.py --platform tiktok --limit 5
    python3 code/scraper/run.py --url https://www.tiktok.com/@example --limit 1
    python3 code/scraper/run.py --input data/input/input_channels.csv --limit 10
    python3 code/scraper/run.py --help
"""

import sys
import argparse
import time
from pathlib import Path

import pandas as pd

# Add project directories to path
# run.py is in code/scraper/, so parent.parent = code/, parent.parent.parent = project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CODE_DIR = _PROJECT_ROOT / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))
if str(CODE_DIR / "scraper") not in sys.path:
    sys.path.insert(0, str(CODE_DIR / "scraper"))

from common import (
    PROJECT_ROOT, INPUT_CSV_FILE, TARGET_COLUMNS, URL_PATTERNS, PLATFORM_ALIASES,
    load_and_clean_csv, get_column_names, enforce_target_columns,
    merge_scraped_row, detect_platform_from_url, merge_to_crm, merge_results_to_crm,
    _now_utc, CRM_FILE, SafeEnricher, backup_crm
)

URL_COL = "ProfileURL"
PLATFORM_COL = "Platform"


# Map platform names to their per-profile extraction functions
# Each entry: (extraction_function, needs_browser, needs_username_from_url)
PER_PROFILE_SCRAPERS = {
    "tiktok": ("scrape_tiktok_profile", True, False),
    "instagram": ("scrape_instagram_playwright", True, False),
    "facebook": ("scrape_facebook_profile", True, False),
    "linkedin": ("scrape_linkedin_profile", True, False),
    "reddit": ("scrape_reddit_profile_playwright", True, True),
    "threads": ("scrape_threads_profile", True, False),
    "youtube": ("scrape_youtube_channel", False, False),
    "vimeo": ("scrape_vimeo_profile", False, False),
    "civitai": ("fetch_civitai_creator", False, True),
}

# Module names for imports
SCRAPER_MODULES = {
    "tiktok": "tiktok",
    "instagram": "instagram",
    "facebook": "facebook",
    "linkedin": "linkedin",
    "reddit": "reddit",
    "threads": "threads",
    "youtube": "main",
    "vimeo": "vimeo",
    "civitai": "civitai",
}


def extract_username_from_url(platform, url):
    """Extract username/handle from URL for platforms that need it."""
    if platform == "reddit":
        import re
        match = re.search(r'reddit\.com/user/([a-zA-Z0-9_\-]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'reddit\.com/u/([a-zA-Z0-9_\-]+)', url)
        if match:
            return match.group(1)
        if url.startswith("u/"):
            return url.replace("u/", "")
        return url.strip().split('/')[-1] if url else None
    elif platform == "civitai":
        import re
        match = re.search(r'civitai\.com/user/([a-zA-Z0-9_\-\.]+)', url)
        if match:
            return match.group(1)
        clean_path = url.strip("/").split("/")
        return clean_path[-1] if clean_path else None
    return None


def dispatch_row(platform, row, page=None, model_provider=None, model_name=None):
    """
    Dispatch a single row to the appropriate scraper's per-profile extraction.
    Returns (success: bool, result: dict or None, error: str or None)
    """
    module_name = SCRAPER_MODULES[platform]
    try:
        module = __import__(module_name)
    except ImportError as e:
        return False, None, f"Failed to import {module_name}: {e}"
    
    func_name, needs_browser, needs_username = PER_PROFILE_SCRAPERS[platform]
    func = getattr(module, func_name)
    
    url = str(row.get("ProfileURL", "")).strip()
    if not url:
        return False, None, "No ProfileURL in row"
    
    try:
        if needs_username:
            username = extract_username_from_url(platform, url)
            if not username:
                return False, None, f"Could not extract username from URL: {url}"
            result = func(username, model_provider=model_provider, model_name=model_name)
        elif needs_browser:
            if page is None:
                return False, None, "Browser required but no page provided"
            result = func(page, url, model_provider=model_provider, model_name=model_name)
        else:
            result = func(url, model_provider=model_provider, model_name=model_name)
        
        return True, result, None
    except TypeError:
        # Fallback for scrapers whose per-profile function doesn't accept model params
        try:
            if needs_username:
                result = func(username)
            elif needs_browser:
                result = func(page, url)
            else:
                result = func(url)
            return True, result, None
        except Exception as fallback_err:
            return False, None, str(fallback_err)
    except Exception as e:
        return False, None, str(e)


def auto_sync_to_sheets():
    """Automatically sync the CRM CSV to Google Sheets.

    Called after a successful scrape/merge operation.
    Performs CSV validation, backup, and incremental append-only sync.

    Safety rules:
    - Append-only: never deletes, clears, or overwrites existing rows.
    - ProfileURL-based deduplication.
    - Zero new creators → no write operation.
    - CSV validation failure → skip sync, report error.
    - Google Sheets API failure → preserve existing sheet data.

    Returns:
        dict with sync summary, or None if sync was skipped/disabled.
    """
    try:
        from sheets.config import load_config
        from sheets.exporter import GoogleSheetsExporter
    except ImportError as e:
        print(f"[i] Google Sheets sync skipped: sheets module not available ({e})")
        return None
    except Exception as e:
        print(f"[!] Google Sheets sync skipped due to import error: {e}")
        return None

    try:
        config = load_config()
    except Exception as e:
        print(f"[i] Google Sheets sync skipped: configuration not available ({e})")
        return None

    try:
        exporter = GoogleSheetsExporter(config)
        result = exporter.export()

        if result.get('new_creators', 0) > 0:
            print(f"[+] Auto-sync: {result['new_creators']} new creator(s) appended to Google Sheets")
        else:
            print(f"[i] Auto-sync: No new creators to export.")

        return result

    except RuntimeError as e:
        # CSV validation failed — do NOT sync
        print(f"[!] Google Sheets sync aborted: CSV validation failed — {e}")
        return None
    except Exception as e:
        # Google Sheets API failure — existing sheet data is untouched
        print(f"[!] Google Sheets sync failed: {e}")
        return None


def auto_sync_reshaped(crm_df: pd.DataFrame) -> dict:
    """Sync re-scraped CRM changes to Google Sheets (column-level updates).

    For existing creators, updates only changed cells.
    For new creators, appends rows (append-only).

    Returns:
        dict with sync summary.
    """
    try:
        from sheets.config import load_config
        from sheets.exporter import GoogleSheetsExporter
    except ImportError:
        print(f"[i] Google Sheets re-scrape sync skipped: sheets module not available")
        return None
    except Exception as e:
        print(f"[!] Google Sheets re-scrape sync skipped: {e}")
        return None

    try:
        config = load_config()
    except Exception:
        print(f"[i] Google Sheets re-scrape sync skipped: configuration not available")
        return None

    try:
        exporter = GoogleSheetsExporter(config)
        result = exporter.export_reshaped(crm_df)

        if result:
            updated = result.get('updated_creators', 0)
            appended = result.get('appended_creators', 0)
            if updated > 0:
                print(f"[+] Re-scrape sync: {updated} creator(s) updated in Google Sheets")
            if appended > 0:
                print(f"[+] Re-scrape sync: {appended} new creator(s) appended to Google Sheets")
            if updated == 0 and appended == 0:
                print(f"[i] Re-scrape sync: No changes to export to Google Sheets")

        return result

    except Exception as e:
        print(f"[!] Google Sheets re-scrape sync failed: {e}")
        return None


def run_batch(input_csv, limit=None, model_provider=None, model_name=None):
    """
    Full-CSV batch dispatch mode.
    Reads CSV, detects platform per row, dispatches to matching scraper.
    """
    if not Path(input_csv).exists():
        print(f"[!] File '{input_csv}' not found.")
        return
    
    print(f"[+] Loading {input_csv}")
    df = load_and_clean_csv(input_csv)
    platform_col, url_col = get_column_names(df)
    
    print(f"[+] Total rows: {len(df)}")
    
    # Categorize rows by platform
    platform_rows = {}
    skipped_rows = []
    for idx, row in df.iterrows():
        url = str(row.get(url_col, "")).strip()
        platform = detect_platform_from_url(url)
        
        if not platform:
            # Try platform column as fallback
            plat_val = str(row.get(platform_col, "")).strip().lower()
            if plat_val in URL_PATTERNS or plat_val in PLATFORM_ALIASES:
                platform = PLATFORM_ALIASES.get(plat_val, plat_val)
        
        if not platform:
            skipped_rows.append((idx, url))
            continue
        
        platform_rows.setdefault(platform, []).append((idx, row))
    
    if skipped_rows:
        print(f"[!] Skipping {len(skipped_rows)} rows with unrecognized platform:")
        for idx, url in skipped_rows[:5]:
            print(f"    Row {idx}: {url}")
        if len(skipped_rows) > 5:
            print(f"    ... and {len(skipped_rows) - 5} more")
    
    print(f"[+] Platforms found: {', '.join(f'{k}({len(v)})' for k, v in sorted(platform_rows.items()))}")
    
    if limit is not None:
        for plat in platform_rows:
            platform_rows[plat] = platform_rows[plat][:limit]
        print(f"[+] Limit set to {limit} rows per platform")
    
    # Process browser-based scrapers (share a single browser session)
    browser_plats = {p for p, (_, needs_browser, _) in PER_PROFILE_SCRAPERS.items() if needs_browser}
    needs_browser = any(p in browser_plats for p in platform_rows)
    
    all_results = {}  # idx -> result dict
    
    if needs_browser:
        from playwright.sync_api import sync_playwright
        from facebook import create_facebook_context
        
        print("[+] Launching browser for browser-based scrapers...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = create_facebook_context(browser)
            page = context.new_page()
            
            for platform in sorted(platform_rows.keys()):
                if platform not in browser_plats:
                    continue
                rows = platform_rows[platform]
                print(f"\n--- Scraping {platform.upper()} ({len(rows)} profiles) ---")
                
                for i, (idx, row) in enumerate(rows, 1):
                    url = str(row[url_col]).strip()
                    print(f"[{i}/{len(rows)}] {platform}: {url}")
                    
                    success, result, error = dispatch_row(platform, row, page=page, model_provider=model_provider, model_name=model_name)
                    
                    if success:
                        all_results[idx] = result
                    else:
                        print(f"    [!] Error: {error}")
                        all_results[idx] = None
                    
                    import time
                    time.sleep(2)
            
            browser.close()
    
    # Process non-browser scrapers (yt-dlp, API)
    for platform in sorted(platform_rows.keys()):
        if platform in browser_plats:
            continue
        rows = platform_rows[platform]
        print(f"\n--- Scraping {platform.upper()} ({len(rows)} profiles) ---")
        
        for i, (idx, row) in enumerate(rows, 1):
            url = str(row[url_col]).strip()
            print(f"[{i}/{len(rows)}] {platform}: {url}")
            
            success, result, error = dispatch_row(platform, row, model_provider=model_provider, model_name=model_name)
            
            if success:
                all_results[idx] = result
            else:
                print(f"    [!] Error: {error}")
                all_results[idx] = None
            
            import time
            time.sleep(1)
    
    # Merge results back into DataFrame
    print("\n[+] Merging results...")
    result_df = df.copy()
    
    # Ensure all TARGET_COLUMNS exist
    for col in TARGET_COLUMNS:
        if col not in result_df.columns:
            result_df[col] = None
    
    for idx, result in all_results.items():
        if result:
            row_dict = result_df.iloc[idx].to_dict()
            row_dict = merge_scraped_row(row_dict, result)
            for key, value in row_dict.items():
                if key in result_df.columns:
                    result_df.at[idx, key] = value
    
    # Write output
    output_csv = PROJECT_ROOT / "data/output/batch_dispatch_output.csv"
    result_df.to_csv(output_csv, index=False)
    print(f"[+] Results saved to {output_csv}")
    print(f"[+] Processed: {len(all_results)} rows | Successful: {sum(1 for r in all_results.values() if r is not None)} | Failed: {sum(1 for r in all_results.values() if r is None)}")
    
    # Merge successful results into master CRM
    successful_results = result_df[result_df["ProfileURL"].notna() & (result_df["ProfileURL"] != "")]
    if len(successful_results) > 0:
        print(f"\n[+] Merging successful results into master CRM...")
        before_count = len(pd.read_csv(PROJECT_ROOT / "data" / "Creator-Intel-CRM-List.csv")) if (PROJECT_ROOT / "data" / "Creator-Intel-CRM-List.csv").exists() else 0
        crm_stats = merge_results_to_crm(successful_results)
        print(f"    CRM: {crm_stats['before_count']} → {crm_stats['after_count']} rows")
        print(f"    Updated: {crm_stats['updated']}, Appended: {crm_stats['appended']}, Skipped: {crm_stats['skipped']}, Pending Review: {crm_stats['pending_review']}")

        # Auto-sync to Google Sheets
        print(f"\n[+] Auto-syncing to Google Sheets...")
        sync_result = auto_sync_to_sheets()
        if sync_result:
            print(f"    Sheets: {sync_result.get('new_creators', 0)} new rows appended")
        else:
            print(f"    Sheets sync skipped or failed (existing data preserved)")


def main():
    parser = argparse.ArgumentParser(
        description="Unified scraper dispatcher for all platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported platforms:
  tiktok, instagram, facebook, linkedin, reddit, threads, youtube, vimeo, civitai

Examples:
  python3 code/scraper/run.py --platform tiktok --limit 5
  python3 code/scraper/run.py --url https://www.tiktok.com/@example --limit 1
  python3 code/scraper/run.py --input data/input/input_channels.csv --limit 10
  python3 code/scraper/run.py --input data/input/input_channels.csv --model-provider api --model-name gpt-5.6
  python3 code/scraper/run.py rescrape --source csv --limit 50 --dry-run
  python3 code/scraper/run.py rescrape --source sheets --limit 25
        """
    )
    
    # Sub-command for rescrape mode
    subparsers = parser.add_subparsers(dest="command")
    
    rescrape_parser = subparsers.add_parser("rescrape", help="Re-scrape existing CRM creators for data enrichment")
    rescrape_parser.add_argument(
        "--source", choices=["csv", "sheets", "auto"], default="csv",
        help="Source of re-scrape queue: csv, sheets, or auto"
    )
    rescrape_parser.add_argument(
        "--limit", type=int, default=None,
        help="Max creators to re-scrape"
    )
    rescrape_parser.add_argument(
        "--offset", type=int, default=0,
        help="Offset for batching"
    )
    rescrape_parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without modifying any files"
    )
    rescrape_parser.add_argument(
        "--model-provider", type=str, default=None,
        help="Override MODEL_PROVIDER"
    )
    rescrape_parser.add_argument(
        "--model-name", type=str, default=None,
        help="Override MODEL_NAME"
    )
    rescrape_parser.add_argument(
        "--no-sync", action="store_true",
        help="Skip Google Sheets sync after re-scrape"
    )
    
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--platform", "-p",
        choices=list(SCRAPER_MODULES.keys()),
        help="Platform to scrape"
    )
    group.add_argument(
        "--url", "-u",
        help="Profile URL (auto-detects platform)"
    )
    group.add_argument(
        "--input", "-i",
        help="Input CSV file for batch dispatch mode (default when no platform/url given)"
    )
    
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Max profiles to process"
    )
    parser.add_argument(
        "--model-provider",
        type=str,
        default=None,
        help="Override MODEL_PROVIDER for this run (e.g. 'api')"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=None,
        help="Override MODEL_NAME for this run (e.g. 'gpt-5.6')"
    )
    
    args = parser.parse_args()
    
    # Handle model override display
    if args.model_provider or args.model_name:
        print(f"[+] Model override: provider={args.model_provider}, model={args.model_name}")
    
    # Re-scrape mode
    if args.command == "rescrape":
        rescrape_creators(
            source=args.source,
            limit=args.limit,
            offset=args.offset,
            dry_run=args.dry_run,
            model_provider=args.model_provider,
            model_name=args.model_name,
            no_sync=args.no_sync,
        )
        return
    
    # Determine mode: --input takes priority, otherwise default to batch if neither platform nor url given
    if args.input or (not args.platform and not args.url):
        # Default to input CSV when no platform/url specified
        input_csv = args.input or str(INPUT_CSV_FILE)
        run_batch(input_csv, limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)
    elif args.platform:
        # Single platform mode
        platform = args.platform.lower()
        module_name = SCRAPER_MODULES[platform]
        try:
            module = __import__(module_name)
        except ImportError as e:
            print(f"[!] Failed to import {module_name}: {e}")
            sys.exit(1)
        
        print(f"[+] Running {platform} scraper (limit={args.limit})...")
        module.main(limit=args.limit, model_provider=args.model_provider, model_name=args.model_name)
    else:
        # URL mode - detect platform and dispatch single profile
        platform = detect_platform_from_url(args.url)
        if not platform:
            print(f"[!] Could not detect platform from URL: {args.url}")
            print(f"[!] Supported domains: {', '.join(URL_PATTERNS.keys())}")
            sys.exit(1)
        print(f"[+] Detected platform: {platform}")
        
        func_name, needs_browser, needs_username = PER_PROFILE_SCRAPERS[platform]
        module_name = SCRAPER_MODULES[platform]
        try:
            module = __import__(module_name)
        except ImportError as e:
            print(f"[!] Failed to import {module_name}: {e}")
            sys.exit(1)

        # Build a single-row DataFrame for dispatch
        single_row = pd.DataFrame([{
            URL_COL: args.url,
            PLATFORM_COL: platform,
        }])
        # Ensure all target columns exist
        for col in TARGET_COLUMNS:
            if col not in single_row.columns:
                single_row[col] = None

        print(f"[+] Dispatching single profile via {func_name}...")
        from playwright.sync_api import sync_playwright
        
        page = None
        browser = None
        if needs_browser:
            from facebook import create_facebook_context
            browser = sync_playwright().start().chromium.launch(headless=True)
            context = create_facebook_context(browser)
            page = context.new_page()
            page.goto(args.url)
            page.wait_for_load_state("domcontentloaded")
            import time
            time.sleep(3)
        
        success, result, error = dispatch_row(
            platform,
            single_row.iloc[0].to_dict(),
            page=page,
            model_provider=args.model_provider,
            model_name=args.model_name,
        )
        
        if browser:
            browser.close()

        if success and result:
            merged = merge_scraped_row(single_row.iloc[0].to_dict(), result)
            result_df = pd.DataFrame([merged])
            result_df = enforce_target_columns(result_df)

            # Generate Source and DiscoveredAt for new records
            result_dict = result_df.iloc[0].to_dict()
            crm_path = Path(CRM_FILE)
            if crm_path.exists():
                import pandas as _pd
                _crm = _pd.read_csv(crm_path)
                profile_url_norm = str(result_dict.get("ProfileURL", "")).strip().lower().rstrip("/")
                existing_mask = _crm["ProfileURL"].astype(str).str.strip().str.lower().str.rstrip("/") == profile_url_norm
                if existing_mask.any():
                    # Existing creator: preserve existing Source and DiscoveredAt
                    existing_row = _crm[existing_mask].iloc[0].to_dict()
                    result_dict["Source"] = existing_row.get("Source") or result_dict.get("Source")
                    result_dict["DiscoveredAt"] = existing_row.get("DiscoveredAt") or result_dict.get("DiscoveredAt")
                else:
                    # New creator: generate Source and DiscoveredAt
                    if not result_dict.get("Source") or result_dict["Source"] in ("", "nan", "None"):
                        result_dict["Source"] = str(platform)
                    if not result_dict.get("DiscoveredAt") or result_dict["DiscoveredAt"] in ("", "nan", "None"):
                        result_dict["DiscoveredAt"] = _now_utc()

            # Merge into master CRM following safe-write procedure
            print(f"[+] Merging into master CRM...")
            before_count, after_count, crm_action = merge_to_crm(result_dict)
            print(f"    CRM: {before_count} → {after_count} rows ({crm_action})")

            # Auto-sync to Google Sheets
            print(f"\n[+] Auto-syncing to Google Sheets...")
            sync_result = auto_sync_to_sheets()
            if sync_result:
                print(f"    Sheets: {sync_result.get('new_creators', 0)} new rows appended")
            else:
                print(f"    Sheets sync skipped or failed (existing data preserved)")
        else:
            print(f"[!] Error scraping profile: {error}")
            result_df = single_row

        # Write output for single URL mode
        output_csv = PROJECT_ROOT / "data/output/run_dispatch_output.csv"
        result_df.to_csv(output_csv, index=False)
        print(f"[+] Results saved to {output_csv}")
        print(f"[+] Processed: 1 | Successful: {1 if success else 0} | Failed: {0 if success else 1}")


def rescrape_creators(source="csv", limit=None, offset=0, dry_run=False,
                      model_provider=None, model_name=None, no_sync=False):
    """Re-scrape existing CRM creators for data enrichment.

    Args:
        source: "csv", "sheets", or "auto"
        limit: Max creators to re-scrape
        offset: Offset for batching
        dry_run: If True, preview changes without writing
        model_provider: Model override
        model_name: Model override
        no_sync: If True, skip Google Sheets sync after re-scrape
    """
    import pandas as pd
    from playwright.sync_api import sync_playwright
    from facebook import create_facebook_context
    from datetime import datetime, timezone
    import time

    print(f"[+] Starting re-scrape mode: source={source}, limit={limit}, offset={offset}, dry_run={dry_run}")

    # ---- STEP 1: Load existing creators ----
    crm_path = Path(CRM_FILE)
    if not crm_path.exists():
        print(f"[!] CRM file not found: {crm_path}")
        return

    # Try loading from Google Sheets if source is "sheets" or "auto"
    if source in ("sheets", "auto"):
        try:
            from sheets.config import load_config
            from sheets.exporter import GoogleSheetsExporter
            config = load_config()
            exporter = GoogleSheetsExporter(config)
            crm_df = exporter._load_csv()
            print(f"[+] Loaded {len(crm_df)} creators from Google Sheets")
            source_used = "sheets"
        except Exception as e:
            print(f"[i] Google Sheets source unavailable ({e}), falling back to CSV")
            crm_df = load_and_clean_csv(str(crm_path))
            source_used = "csv"
    else:
        crm_df = load_and_clean_csv(str(crm_path))
        source_used = "csv"

    print(f"[+] Total existing creators: {len(crm_df)}")

    # Validate ProfileURLs
    valid_mask = crm_df["ProfileURL"].astype(str).str.strip().str.len() > 0
    crm_df = crm_df[valid_mask].copy()
    print(f"[+] Valid creators with ProfileURLs: {len(crm_df)}")

    # Apply offset and limit
    crm_df = crm_df.iloc[offset:]
    if limit is not None:
        crm_df = crm_df.head(limit)

    print(f"[+] Processing {len(crm_df)} creator(s) for re-scrape...")

    # ---- STEP 2: Build platform groups for dispatching ----
    platform_groups = {}
    for idx, row in crm_df.iterrows():
        url = str(row.get("ProfileURL", "")).strip()
        platform = detect_platform_from_url(url)
        if not platform:
            plat_val = str(row.get("Platform", "")).strip().lower()
            if plat_val in URL_PATTERNS or plat_val in PLATFORM_ALIASES:
                platform = PLATFORM_ALIASES.get(plat_val, plat_val)
        if platform and url:
            platform_groups.setdefault(platform, []).append((idx, url, row.to_dict()))

    if not platform_groups:
        print(f"[!] No valid creators with recognized platforms found.")
        return

    print(f"[+] Platforms to process: {', '.join(f'{k}({len(v)})' for k, v in sorted(platform_groups.items()))}")

    # ---- STEP 3: Re-scrape each creator ----
    enriched_rows = []
    change_report = []
    failed = []

    browser_plats = {p for p, (_, needs_browser, _) in PER_PROFILE_SCRAPERS.items() if needs_browser}
    needs_browser = any(p in browser_plats for p in platform_groups)

    if needs_browser:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = create_facebook_context(browser)
            page = context.new_page()

            for platform in sorted(platform_groups.keys()):
                if platform not in browser_plats:
                    continue
                rows = platform_groups[platform]
                print(f"\n--- Re-scraping {platform.upper()} ({len(rows)} profiles) ---")
                _scrape_platform_rows(
                    platform, rows, page, crm_df, enriched_rows,
                    change_report, failed, model_provider, model_name,
                    dry_run, browser_plats
                )
                time.sleep(1)

            browser.close()
    else:
        for platform in sorted(platform_groups.keys()):
            if platform in browser_plats:
                continue
            rows = platform_groups[platform]
            print(f"\n--- Re-scraping {platform.upper()} ({len(rows)} profiles) ---")
            _scrape_platform_rows(
                platform, rows, None, crm_df, enriched_rows,
                change_report, failed, model_provider, model_name,
                dry_run, browser_plats
            )
            time.sleep(1)

    # ---- STEP 4: Merge enriched data back into CRM ----
    if not dry_run and enriched_rows:
        print(f"\n[+] Merging {len(enriched_rows)} enriched results into CRM...")
        before_count = len(pd.read_csv(crm_path))

        # Create backup BEFORE modifying CRM
        backup_path = backup_crm(crm_path)
        print(f"    Backup: {backup_path}")

        # Create a DataFrame from enriched rows and merge
        results_df = pd.DataFrame(enriched_rows)
        results_df = enforce_target_columns(results_df)

        # Merge each enriched row into CRM
        crm_df_existing = pd.read_csv(crm_path)
        for _, row in results_df.iterrows():
            row_dict = row.to_dict()
            profile_url = str(row_dict.get("ProfileURL", "")).strip()
            profile_url_norm = profile_url.lower().rstrip("/")
            existing_mask = crm_df_existing["ProfileURL"].astype(str).str.strip().str.lower().str.rstrip("/") == profile_url_norm

            if existing_mask.any():
                # Update existing row
                idx = existing_mask[existing_mask].index[0]
                existing_row = crm_df_existing.iloc[idx].to_dict()
                # Build scraped_data from the enriched row (strip immutable fields)
                scraped_data = {}
                for col in TARGET_COLUMNS:
                    if col not in SafeEnricher.IMMUTABLE_FIELDS:
                        scraped_data[col] = row_dict.get(col)
                enricher = SafeEnricher()
                merged, changes = enricher.enrich(existing_row, scraped_data, scrape_successful=True)
                for key, value in merged.items():
                    if key in crm_df_existing.columns:
                        crm_df_existing.at[idx, key] = value
            else:
                # Should not happen in re-scrape mode, but handle gracefully
                crm_df_existing = pd.concat([crm_df_existing, pd.DataFrame([row_dict])], ignore_index=True)

        # Validate and write
        crm_df_existing = crm_df_existing[TARGET_COLUMNS]
        assert len(crm_df_existing) >= before_count, "Row count decreased after re-scrape!"
        crm_df_existing.to_csv(crm_path, index=False)
        after_count = len(pd.read_csv(crm_path))
        print(f"    CRM: {before_count} → {after_count} rows")

        # ---- STEP 5: Google Sheets column-level sync ----
        if not dry_run and not no_sync:
            print(f"\n[+] Syncing changes to Google Sheets...")
            sync_result = auto_sync_reshaped(crm_df_existing)
            if sync_result:
                print(f"    Google Sheets sync completed")
            else:
                print(f"    Google Sheets sync skipped (existing data preserved)")
    elif dry_run:
        print(f"\n[DRY RUN] No files modified.")
        print(f"[DRY RUN] Would merge {len(enriched_rows)} enriched records")
        print(f"[DRY RUN] Failed: {len(failed)} creators")

    # ---- STEP 6: Report ----
    print(f"\n{'='*60}")
    print(f"RE-SCRAPE REPORT")
    print(f"{'='*60}")
    print(f"Source: {source_used}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Creators processed: {len(crm_df)}")
    print(f"Successfully enriched: {len(enriched_rows)}")
    print(f"Failed: {len(failed)}")
    print(f"\nChanges:")
    for change in change_report[:20]:  # Show first 20
        print(f"  {change['field']}: {change['old_value']} → {change['new_value']} ({change['status']})")
    if len(change_report) > 20:
        print(f"  ... and {len(change_report) - 20} more changes")

    if failed:
        print(f"\nFailed creators:")
        for f in failed[:10]:
            print(f"  {f}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")

    print(f"\n{'='*60}")
    if dry_run:
        print(f"DRY RUN COMPLETE — no files modified")
    else:
        print(f"RE-SCRAPE COMPLETE — CRM updated, backups created")


def _scrape_platform_rows(platform, rows, page, crm_df, enriched_rows,
                           change_report, failed, model_provider, model_name,
                           dry_run, browser_plats, scrape_successful_list=None):
    """Helper: scrape multiple rows for a platform and collect enriched results.

    Args:
        platform: Platform name key
        rows: List of (idx, url, row_dict) tuples
        page: Playwright page object (or None for non-browser scrapers)
        crm_df: Original CRM DataFrame for reference
        enriched_rows: List to append enriched row dicts to
        change_report: List to append change dicts to
        failed: List to append failed profile URLs to
        model_provider: Model override
        model_name: Model override
        dry_run: If True, scrape but don't write
        browser_plats: Set of browser-based platform names
        scrape_successful_list: Optional list to track success status
    """
    from common import normalize_scraped_result, SafeEnricher

    for i, (idx, url, row_dict) in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {platform}: {url}")

        # Get existing CRM data for this creator
        profile_url_norm = url.strip().lower().rstrip("/")
        existing_mask = crm_df["ProfileURL"].astype(str).str.strip().str.lower().str.rstrip("/") == profile_url_norm

        if not existing_mask.any():
            print(f"    [!] Creator not found in CRM, skipping")
            failed.append(url)
            continue

        existing_row = crm_df[existing_mask].iloc[0].to_dict()

        # Dispatch to scraper
        try:
            if platform in ["reddit", "civitai"]:
                username = extract_username_from_url(platform, url)
                if not username:
                    print(f"    [!] Could not extract username")
                    failed.append(url)
                    continue
                success, result, error = dispatch_row(platform, row_dict, model_provider=model_provider, model_name=model_name)
            elif platform in browser_plats:
                if page is None:
                    print(f"    [!] Browser required but no page provided")
                    failed.append(url)
                    continue
                success, result, error = dispatch_row(platform, row_dict, page=page, model_provider=model_provider, model_name=model_name)
            else:
                success, result, error = dispatch_row(platform, row_dict, model_provider=model_provider, model_name=model_name)
        except Exception as e:
            print(f"    [!] Scrape error: {e}")
            failed.append(url)
            continue

        if not success or not result:
            print(f"    [!] Scrape failed: {error}")
            failed.append(url)
            continue

        # Normalize scraped data
        result = normalize_scraped_result(result)

        # Build scraped data for enrichment (exclude immutable fields)
        scraped_for_enrich = {}
        for col in TARGET_COLUMNS:
            if col not in SafeEnricher.IMMUTABLE_FIELDS:
                scraped_for_enrich[col] = result.get(col)

        # Add existing immutable values that scraper might not have returned
        for col in SafeEnricher.IMMUTABLE_FIELDS - {"ProfileURL"}:
            if col not in scraped_for_enrich or is_val_empty(scraped_for_enrich.get(col)):
                scraped_for_enrich[col] = existing_row.get(col, "")

        # Ensure ProfileURL is the existing one
        scraped_for_enrich["ProfileURL"] = existing_row.get("ProfileURL", "")

        # Enrich
        enricher = SafeEnricher()
        enriched, changes = enricher.enrich(existing_row, scraped_for_enrich, scrape_successful=True)

        enriched["LastScrapedAt"] = enricher._now_utc()

        # Collect changes
        for change in changes:
            change["profile_url"] = url
            change_report.append(change)

        enriched_rows.append(enriched)
        print(f"    [+] Enriched: {len(changes)} changes detected")

        if scrape_successful_list is not None:
            scrape_successful_list.append(True)

        time.sleep(2)  # Rate limiting


def is_val_empty(val) -> bool:
    """Check if a value is truly empty/unavailable (NaN-safe)."""
    if val is None:
        return True
    s = str(val).strip()
    return s in ("", "None", "N/A", "nan", "NaN", "null", "NULL")


if __name__ == "__main__":
    main()
