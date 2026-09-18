"""Google Sheets export module for the Creator Research System.

Provides one-way CSV -> Google Sheets synchronization.
Google Sheets is NOT the source of truth; CSV remains the master.
"""

import sys
from pathlib import Path

# Add code directory to sys.path so 'sheets' can be imported directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CODE_DIR = _PROJECT_ROOT / "code"
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

from sheets.config import (
    GOOGLE_SHEETS_SPREADSHEET_ID,
    GOOGLE_SHEETS_TAB_NAME,
    GOOGLE_SHEETS_RANGE,
    load_config,
)
from sheets.client import GoogleSheetsClient
from sheets.exporter import GoogleSheetsExporter, export_sheets


def export_to_sheets():
    """Run the full Google Sheets export pipeline.

    Returns:
        dict with export summary, or raises RuntimeError on failure.
    """
    config = load_config()
    exporter = GoogleSheetsExporter(config)
    return exporter.export()


__all__ = [
    "export_to_sheets",
    "export_sheets",
    "GoogleSheetsClient",
    "GoogleSheetsExporter",
    "load_config",
    "GOOGLE_SHEETS_SPREADSHEET_ID",
    "GOOGLE_SHEETS_TAB_NAME",
    "GOOGLE_SHEETS_RANGE",
]