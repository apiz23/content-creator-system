#!/usr/bin/env python3
"""
Unified scraper dispatcher with full-CSV batch dispatch.

Usage:
    python3 Code/scraper/run.py --platform tiktok --limit 5
    python3 Code/scraper/run.py --url https://www.tiktok.com/@example --limit 1
    python3 Code/scraper/run.py --input data/input/input_channels.csv --limit 10
    python3 Code/scraper/run.py --help
"""

import sys
import argparse
from pathlib import Path

import pandas as pd

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (
    PROJECT_ROOT, INPUT_CSV_FILE, TARGET_COLUMNS, URL_PATTERNS, PLATFORM_ALIASES,
    load_and_clean_csv, get_column_names, enforce_target_columns,
    merge_scraped_row, detect_platform_from_url, merge_to_crm, merge_results_to_crm
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


def main():
    parser = argparse.ArgumentParser(
        description="Unified scraper dispatcher for all platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported platforms:
  tiktok, instagram, facebook, linkedin, reddit, threads, youtube, vimeo, civitai

Examples:
  python3 Code/scraper/run.py --platform tiktok --limit 5
  python3 Code/scraper/run.py --url https://www.tiktok.com/@example --limit 1
  python3 Code/scraper/run.py --input data/input/input_channels.csv --limit 10
  python3 Code/scraper/run.py --input data/input/input_channels.csv --model-provider api --model-name gpt-5.6
        """
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
            
            # Merge into master CRM following safe-write procedure
            print(f"[+] Merging into master CRM...")
            before_count, after_count, crm_action = merge_to_crm(
                result_df.iloc[0].to_dict()
            )
            print(f"    CRM: {before_count} → {after_count} rows ({crm_action})")
        else:
            print(f"[!] Error scraping profile: {error}")
            result_df = single_row

        # Write output for single URL mode
        output_csv = PROJECT_ROOT / "data/output/run_dispatch_output.csv"
        result_df.to_csv(output_csv, index=False)
        print(f"[+] Results saved to {output_csv}")
        print(f"[+] Processed: 1 | Successful: {1 if success else 0} | Failed: {0 if success else 1}")


if __name__ == "__main__":
    main()
