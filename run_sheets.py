#!/usr/bin/env python3
"""Runner script for Google Sheets export and re-scrape.

Usage:
    python run_sheets.py export          # Export CRM to Google Sheets
    python run_sheets.py backup          # Create CSV backup only
    python run_sheets.py rescrape --source csv   # Re-scrape existing CRM creators
    python run_sheets.py rescrape --source sheets --limit 25 --dry-run
    python run_sheets.py --help          # Show help
"""

import sys
from pathlib import Path

# Add code directory to sys.path so 'sheets' can be imported
PROJECT_ROOT = Path(__file__).resolve().parent
CODE_DIR = PROJECT_ROOT / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from sheets.config import load_config
from sheets.exporter import GoogleSheetsExporter, export_reshaped
from scraper.common import backup_crm


def cmd_export():
    """Export CRM CSV data to Google Sheets."""
    config = load_config()
    exporter = GoogleSheetsExporter(config)
    result = exporter.export()

    print("Google Sheets export completed.")
    print()
    print(f"Spreadsheet: {result['spreadsheet_id']}")
    print(f"Tab: {result['tab_name']}")
    if result.get('message'):
        print(f"Message: {result['message']}")
    else:
        existing = result.get('existing_rows', 0)
        new_count = result.get('rows_appended', 0)
        csv_rows = result.get('csv_rows', 0)
        print(f"Existing Google Sheet rows: {existing}")
        print(f"CSV rows: {csv_rows}")
        print(f"New creators detected: {new_count}")
        print(f"Rows appended: {new_count}")
        print(f"Columns: 19")
    print(f"Backup: {result['backup_path']}")
    if result.get('verification'):
        v = result['verification']
        print(f"Verification: {v['rows_read']} rows read back")


def cmd_backup():
    """Create a timestamped backup of the CRM CSV."""
    backup_path = backup_crm()
    print(f"Backup created: {backup_path}")


def cmd_reshaped(remaining=None):
    """Re-scrape existing CRM creators and sync to Google Sheets."""
    import argparse
    from scraper.common import SafeEnricher, load_and_clean_csv
    from scraper.run import CRM_FILE

    parser = argparse.ArgumentParser(description="Re-scrape existing CRM creators")
    parser.add_argument("--source", choices=["csv", "sheets", "auto"], default="csv",
                        help="Source of re-scrape queue")
    parser.add_argument("--limit", type=int, default=None, help="Max creators to re-scrape")
    parser.add_argument("--offset", type=int, default=0, help="Offset for batching")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying")
    parser.add_argument("--model-provider", type=str, default=None, help="Override MODEL_PROVIDER")
    parser.add_argument("--model-name", type=str, default=None, help="Override MODEL_NAME")
    parser.add_argument("--no-sync", action="store_true", help="Skip Google Sheets sync")
    args = parser.parse_args(remaining or [])

    # Use the rescrape_creators function from run.py
    from scraper.run import rescrape_creators
    rescrape_creators(
        source=args.source,
        limit=args.limit,
        offset=args.offset,
        dry_run=args.dry_run,
        model_provider=args.model_provider,
        model_name=args.model_name,
        no_sync=args.no_sync,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Google Sheets export for Creator Research System"
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["export", "backup", "rescrape"],
        help="Command to run",
    )
    # Use parse_known_args to pass through all sub-command arguments
    args, remaining = parser.parse_known_args()

    if not args.command:
        parser.print_help()
        print()
        print("Commands:")
        print("  export     - Push CRM CSV data to Google Sheets")
        print("  backup     - Create a timestamped backup of the CRM CSV")
        print("  rescrape   - Re-scrape existing CRM creators for enrichment")
        return

    try:
        if args.command == "export":
            cmd_export()
        elif args.command == "backup":
            cmd_backup()
        elif args.command == "rescrape":
            cmd_reshaped(remaining)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()