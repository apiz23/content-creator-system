"""Configuration loading for Google Sheets integration.

Reads settings from .env and environment variables.
All credentials are loaded from environment or local credential files.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (code/sheets/ → code/ → project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# --- Required configuration ---

GOOGLE_SHEETS_SPREADSHEET_ID = os.environ.get(
    "GOOGLE_SHEETS_SPREADSHEET_ID", ""
).strip()

GOOGLE_SHEETS_TAB_NAME = os.environ.get(
    "GOOGLE_SHEETS_TAB_NAME", ""
).strip()

# Optional: explicit range override (e.g. "Creator Intel!A:S")
# If not set, range is auto-generated from tab name and column count.
GOOGLE_SHEETS_RANGE = os.environ.get(
    "GOOGLE_SHEETS_RANGE", ""
).strip()

# --- Credential paths ---
# Default locations for Google OAuth credentials.
# The user places credentials.json here manually.
CREDENTIALS_FILE = _PROJECT_ROOT / "credentials.json"
TOKEN_FILE = _PROJECT_ROOT / "token.json"


@dataclass
class SheetsConfig:
    """Configuration for the Google Sheets exporter."""

    spreadsheet_id: str
    tab_name: str
    credentials_path: Path
    token_path: Path
    range_override: str = ""

    @property
    def range(self) -> str:
        """Generate the sheet range from tab name and column count.

        Format: 'Tab Name'!A:S for 19 columns (A through S).
        """
        if self.range_override:
            return self.range_override
        # 19 columns = A through S
        column_letter = "S"  # 19th column
        return f"'{self.tab_name}'!A:{column_letter}"

    def validate(self) -> list[str]:
        """Validate configuration and return a list of errors."""
        errors: list[str] = []
        if not self.spreadsheet_id:
            errors.append("GOOGLE_SHEETS_SPREADSHEET_ID is not configured.")
        if not self.tab_name:
            errors.append("GOOGLE_SHEETS_TAB_NAME is not configured.")
        if not self.credentials_path.exists():
            errors.append(
                f"Credentials file not found: {self.credentials_path}\n"
                "Please create credentials.json from Google Cloud Console.\n"
                "See README.md for setup instructions."
            )
        return errors


def load_config() -> SheetsConfig:
    """Load and validate Google Sheets configuration.

    Raises:
        RuntimeError: If required configuration is missing.
    """
    config = SheetsConfig(
        spreadsheet_id=GOOGLE_SHEETS_SPREADSHEET_ID,
        tab_name=GOOGLE_SHEETS_TAB_NAME,
        credentials_path=CREDENTIALS_FILE,
        token_path=TOKEN_FILE,
        range_override=GOOGLE_SHEETS_RANGE,
    )

    errors = config.validate()
    if errors:
        raise RuntimeError(
            "Google Sheets configuration errors:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    return config