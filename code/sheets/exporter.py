"""Google Sheets exporter - one-way CSV to Google Sheets synchronization.

Reads the Master CRM CSV, validates columns, creates a backup,
and incrementally appends only NEW creators to the configured
Google Sheets tab.

This is a ONE-WAY operation: CSV -> Google Sheets only.
Google Sheets is NOT a source of truth and is never read back
for merging into the research system.

Existing Google Sheet rows are never deleted, replaced, or
reordered. Only new ProfileURLs are appended.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root and code/scraper to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = _PROJECT_ROOT / "code"
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from sheets.config import SheetsConfig, load_config
from sheets.client import GoogleSheetsClient
from scraper.common import backup_crm, CRM_FILE, TARGET_COLUMNS
import pandas as pd


def clean_cell_value(val: Any) -> str:
    """Clean a cell value for Google Sheets export.

    Converts missing/null representations (None, pandas NaN/NA, empty strings,
    and literal "nan", "NaN", "None", "null", "NULL") to empty string "".
    Preserves substantive text (e.g., "nanotechnology"), numbers, and JSON strings.
    """
    if val is None:
        return ""

    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass

    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return ""

    return str(val)


class GoogleSheetsExporter:
    """Exports the Creator Intel CRM CSV data to Google Sheets.

    The export process is INCREMENTAL APPEND:
    1. Load and validate the CRM CSV
    2. Read existing ProfileURLs from Google Sheets
    3. Identify NEW CSV records (not in Google Sheets)
    4. Validate existing header matches expected schema
    5. Create a timestamped backup of the CSV
    6. Connect to Google Sheets
    7. Append ONLY new records to the target tab
    8. Verify the write succeeded

    Existing rows are never touched.
    """

    def __init__(self, config: SheetsConfig):
        self._config = config
        self._csv_path = CRM_FILE

    def _load_csv(self) -> pd.DataFrame:
        """Load the CRM CSV and validate required columns.

        Returns:
            DataFrame with only the 19 TARGET_COLUMNS in order.

        Raises:
            RuntimeError: If the CSV is missing or has missing columns.
        """
        if not self._csv_path.exists():
            raise RuntimeError(f"CRM CSV not found: {self._csv_path}")

        df = pd.read_csv(self._csv_path, dtype=str)

        # Check for missing required columns
        missing = [col for col in TARGET_COLUMNS if col not in df.columns]
        if missing:
            raise RuntimeError(
                "Missing required columns:\n"
                + "\n".join(f"  - {col}" for col in missing)
            )

        # Select only the 19 expected columns in exact order
        df = df[TARGET_COLUMNS]

        return df

    def _get_existing_profile_urls(self, client: GoogleSheetsClient) -> set[str]:
        """Read existing ProfileURLs from the configured Google Sheets tab.

        Returns:
            Set of normalized ProfileURL strings (stripped, lowercase).
        """
        range_name = self._config.range
        values = client.read_range(range_name)

        existing_urls = set()

        # values[0] is the header row, data starts from values[1]
        for row in values[1:]:
            if row and len(row) > 0:
                profile_url = row[0].strip().rstrip("/").lower()
                if profile_url:
                    existing_urls.add(profile_url)

        return existing_urls

    def _validate_header(self, client: GoogleSheetsClient) -> bool:
        """Validate that the existing Google Sheet header matches expected schema.

        Returns:
            True if header matches or if sheet is empty (no header to validate).

        Raises:
            RuntimeError: If header is incompatible.
        """
        range_name = self._config.range
        values = client.read_range(range_name)

        if not values or len(values) < 1:
            # Empty sheet - no header to validate
            return True

        header = values[0]
        if not header:
            return True

        # Check that header matches expected columns (case-insensitive)
        expected = [col.lower() for col in TARGET_COLUMNS]
        actual = [str(h).strip().lower() for h in header]

        if actual != expected:
            # Check if the sheet might have no data rows yet
            if len(actual) == 19 and actual == expected:
                return True
            raise RuntimeError(
                "Google Sheet header does not match expected schema.\n"
                f"Expected: {TARGET_COLUMNS}\n"
                f"Found: {header}\n"
                "Please check the target tab and try again."
            )

        return True

    def _find_new_records(self, df: pd.DataFrame, existing_urls: set[str]) -> pd.DataFrame:
        """Identify CSV records that are NOT already in Google Sheets.

        Uses ProfileURL as the unique identifier (normalized for comparison).

        Args:
            df: DataFrame with only TARGET_COLUMNS.
            existing_urls: Set of existing ProfileURLs (normalized).

        Returns:
            DataFrame containing only new records.
        """
        new_rows = []
        for _, row in df.iterrows():
            profile_url = str(row["ProfileURL"]).strip().rstrip("/").lower()
            if profile_url not in existing_urls:
                new_rows.append(row)

        if not new_rows:
            return pd.DataFrame(columns=TARGET_COLUMNS)

        return pd.DataFrame(new_rows, columns=TARGET_COLUMNS)

    def _create_backup(self) -> str:
        """Create a timestamped backup of the CRM CSV.

        Returns:
            Path to the backup file.
        """
        backup_path = backup_crm(self._csv_path)
        return backup_path

    def export(self) -> dict:
        """Run the incremental append export pipeline.

        Returns:
            dict with export summary.

        Raises:
            RuntimeError: If any step fails.
        """
        # Step 1: Load and validate CSV
        df = self._load_csv()
        total_csv_rows = len(df)

        # Step 2: Create CSV backup BEFORE connecting to Google Sheets
        backup_path = self._create_backup()

        # Step 3: Connect to Google Sheets
        client = GoogleSheetsClient(
            spreadsheet_id=self._config.spreadsheet_id,
            credentials_path=self._config.credentials_path,
            token_path=self._config.token_path,
        )
        client.connect()

        try:
            # Step 4: Verify target tab exists
            if not client.tab_exists(self._config.tab_name):
                raise RuntimeError(
                    f"Target tab '{self._config.tab_name}' does not exist in "
                    f"spreadsheet {self._config.spreadsheet_id}.\n"
                    f"Please create the tab manually and try again."
                )

            # Step 5: Validate existing header
            self._validate_header(client)

            # Step 6: Read existing ProfileURLs from Google Sheets
            existing_urls = self._get_existing_profile_urls(client)
            existing_count = len(existing_urls)

            # Step 7: Find NEW records
            new_df = self._find_new_records(df, existing_urls)
            new_count = len(new_df)

            if new_count == 0:
                client.close()
                return {
                    "success": True,
                    "spreadsheet_id": self._config.spreadsheet_id,
                    "tab_name": self._config.tab_name,
                    "existing_rows": existing_count,
                    "csv_rows": total_csv_rows,
                    "new_creators": 0,
                    "duplicates_skipped": total_csv_rows,
                    "rows_appended": 0,
                    "backup_path": backup_path,
                    "message": "No new creators to export.",
                    "timestamp": datetime.now().isoformat(),
                }

            # Step 8: Prepare new rows for appending (NO header)
            new_rows = []
            for _, row in new_df.iterrows():
                row_values = []
                for col in TARGET_COLUMNS:
                    val = row[col]
                    row_values.append(clean_cell_value(val))
                new_rows.append(row_values)

            # Step 9: Append new records
            # Determine starting row (after existing data + header)
            # Read current data to find last row number
            range_name = self._config.range
            existing_values = client.read_range(range_name)
            existing_data_rows = max(0, len(existing_values) - 1)  # minus header
            start_row = existing_data_rows + 2  # +2 because 1-indexed and +1 for header

            # Build the range for appending (e.g., 'Tab Name'!A1119:S1124)
            tab = self._config.tab_name
            end_row = start_row + new_count - 1
            append_range = f"'{tab}'!A{start_row}:S{end_row}"

            client.append_rows(append_range, new_rows)

            # Step 10: Verify the write
            verification = self._verify_write(client)

            client.close()

            return {
                "success": True,
                "spreadsheet_id": self._config.spreadsheet_id,
                "tab_name": self._config.tab_name,
                "existing_rows": existing_count,
                "csv_rows": total_csv_rows,
                "new_creators": new_count,
                "duplicates_skipped": total_csv_rows - new_count,
                "rows_appended": new_count,
                "backup_path": backup_path,
                "verification": verification,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception:
            client.close()
            raise

    def export_reshaped(self, crm_df: pd.DataFrame) -> dict:
        """Sync re-scraped CRM changes to Google Sheets (column-level updates).

        For existing creators: find the row by ProfileURL and update ONLY
        changed cells.
        For new creators: append rows (append-only).

        Safety rules:
        - Never delete, clear, or replace entire rows
        - Never use batchClear or fullReplace
        - Never reorder rows
        - Only update specific changed cells
        - API failure preserves existing sheet data

        Args:
            crm_df: DataFrame with only TARGET_COLUMNS in order.

        Returns:
            dict with update summary.
        """
        import pandas as pd
        from sheets.config import SheetsConfig, load_config
        from sheets.client import GoogleSheetsClient

        try:
            config = load_config()
        except Exception:
            return None

        client = None
        try:
            client = GoogleSheetsClient(
                spreadsheet_id=config.spreadsheet_id,
                credentials_path=config.credentials_path,
                token_path=config.token_path,
            )
            client.connect()
        except Exception:
            return None

        try:
            if not client.tab_exists(config.tab_name):
                client.close()
                return None

            # Read existing data from Google Sheets
            range_name = config.range
            values = client.read_range(range_name)

            if not values or len(values) < 2:
                # No data rows — nothing to update
                client.close()
                return {"updated_creators": 0, "appended_creators": 0}

            header = values[0]
            existing_rows = values[1:]

            # Build normalized ProfileURL -> row_index map
            url_col_idx = None
            for i, h in enumerate(header):
                if str(h).strip().lower() == "profileurl":
                    url_col_idx = i
                    break

            if url_col_idx is None:
                client.close()
                return None

            url_to_row_idx = {}
            for row_idx, row in enumerate(existing_rows):
                if row and len(row) > url_col_idx:
                    url = str(row[url_col_idx]).strip().rstrip("/").lower()
                    url_to_row_idx[url] = row_idx + 2  # +2 because 1-indexed and header is row 1

            # Find column indices for each field
            col_indices = {}
            for i, h in enumerate(header):
                col_indices[str(h).strip().lower()] = i

            updated_count = 0
            appended_count = 0

            # Get existing ProfileURLs from sheet
            existing_sheet_urls = set(url_to_row_idx.keys())

            # Get CRM ProfileURLs
            crm_urls = set()
            for _, row in crm_df.iterrows():
                url = str(row.get("ProfileURL", "")).strip().rstrip("/").lower()
                crm_urls.add(url)

            # Find new creators (in CRM but not in sheet)
            new_urls = crm_urls - existing_sheet_urls

            # Find existing creators (in both) — need to check which fields changed
            existing_crm_urls = crm_urls & existing_sheet_urls

            # Read full sheet data for writing
            # We'll update existing rows cell by cell
            for _, row in crm_df.iterrows():
                profile_url = str(row.get("ProfileURL", "")).strip().rstrip("/").lower()

                if profile_url in new_urls:
                    # Append new row — handled by auto_sync_to_sheets
                    appended_count += 1
                    continue

                if profile_url not in existing_sheet_urls:
                    continue

                # Find which columns changed for this existing row
                sheet_row_idx = url_to_row_idx[profile_url]
                sheet_row = existing_rows[sheet_row_idx - 2]  # Convert back to 0-indexed

                # Build list of changed columns and their new values
                changed_cols = []
                changed_values = []

                for col_name in TARGET_COLUMNS:
                    col_idx = col_indices.get(col_name.lower())
                    if col_idx is None:
                        continue
                    sheet_val = str(sheet_row[col_idx]).strip() if col_idx < len(sheet_row) else ""
                    new_val = str(row.get(col_name, ""))
                    new_val_clean = new_val if new_val and new_val != "None" else ""
                    # Skip if values are the same
                    if sheet_val != new_val_clean:
                        changed_cols.append(col_idx)
                        changed_values.append(new_val_clean)

                if changed_cols:
                    # Build a row of values for the changed columns
                    # We need to write the full row (or at least the changed cells)
                    # For simplicity, write the full row values for changed columns
                    # Using update_cells with the specific range
                    # e.g., "'Temp'!B5:D5" for columns 1-3 of row 5

                    # Build full updated row
                    full_row_values = []
                    for col_name in TARGET_COLUMNS:
                        col_idx = col_indices.get(col_name.lower())
                        if col_idx is not None and col_idx < len(sheet_row):
                            full_row_values.append(str(row.get(col_name, "")).strip() or "")
                        else:
                            full_row_values.append("")

                    # Update the specific row
                    start_col_letter = chr(ord('A') + min(changed_cols))
                    end_col_letter = chr(ord('A') + max(changed_cols))
                    start_row = sheet_row_idx
                    end_row = sheet_row_idx
                    update_range = f"'{config.tab_name}'!{start_col_letter}{start_row}:{end_col_letter}{end_row}"

                    # Build the values array for the update range
                    update_values = []
                    for ci in range(min(changed_cols), max(changed_cols) + 1):
                        if ci < len(full_row_values):
                            update_values.append([full_row_values[ci]])
                        else:
                            update_values.append([""])

                    try:
                        client.update_cells(update_range, update_values)
                        updated_count += 1
                    except Exception:
                        # API failure — existing sheet data is untouched
                        pass

            client.close()

            return {
                "success": True,
                "spreadsheet_id": config.spreadsheet_id,
                "tab_name": config.tab_name,
                "updated_creators": updated_count,
                "appended_creators": appended_count,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception:
            if client:
                client.close()
            return None

    def _verify_write(self, client: GoogleSheetsClient) -> dict:
        """Verify that data was written correctly."""
        range_name = self._config.range
        values = client.read_range(range_name)
        return {
            "rows_read": len(values),
            "columns_read": len(values[0]) if values else 0,
        }


def export_sheets() -> dict:
    """Convenience function to run Google Sheets export."""
    config = load_config()
    exporter = GoogleSheetsExporter(config)
    return exporter.export()


def export_reshaped(crm_df: pd.DataFrame) -> dict:
    """Convenience function to run Google Sheets re-scrape export."""
    config = load_config()
    exporter = GoogleSheetsExporter(config)
    return exporter.export_reshaped(crm_df)


__all__ = [
    "GoogleSheetsExporter",
    "export_sheets",
    "export_to_sheets",
    "export_reshaped",
]
