"""Configuration loading for Google Sheets integration.

Reads settings from .env and environment variables.
No credentials are stored in this repository.
All Google Sheets operations go through the Hermes google_api.py wrapper.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# --- Required configuration ---

GOOGLE_SHEETS_SPREADSHEET_ID = os.environ.get(
    "GOOGLE_SHEETS_SPREADSHEET_ID", ""
).strip()

GOOGLE_SHEETS_TAB_NAME = os.environ.get(
    "GOOGLE_SHEETS_TAB_NAME", ""
).strip()

# Optional: explicit range override (e.g. "'Creator Intel'!A:S")
# If not set, range is auto-generated from tab name and column count.
GOOGLE_SHEETS_RANGE = os.environ.get(
    "GOOGLE_SHEETS_RANGE", ""
).strip()

# --- Hermes Google Sheets CLI configuration ---
# These paths point to the existing Hermes installation on the
# supervisor's Mac Mini. They are optional during local development
# and are only needed when an actual Google Sheets operation is
# attempted.

HERMES_GOOGLE_API_PYTHON = os.environ.get(
    "HERMES_GOOGLE_API_PYTHON", ""
).strip()

HERMES_GOOGLE_API_SCRIPT = os.environ.get(
    "HERMES_GOOGLE_API_SCRIPT", ""
).strip()


@dataclass
class SheetsConfig:
    """Configuration for the Google Sheets exporter.

    Does not require credentials.json or token.json.
    All authentication is handled by the Hermes installation.
    """

    spreadsheet_id: str
    tab_name: str
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
        """Validate configuration and return a list of errors.

        Does NOT check for credentials — the Hermes wrapper
        handles authentication.
        """
        errors: list[str] = []
        if not self.spreadsheet_id:
            errors.append(
                "GOOGLE_SHEETS_SPREADSHEET_ID is not configured."
            )
        if not self.tab_name:
            errors.append(
                "GOOGLE_SHEETS_TAB_NAME is not configured."
            )
        return errors

    def validate_adapter(self) -> list[str]:
        """Validate that the Hermes google_api.py adapter is configured.

        Returns:
            List of adapter configuration errors.
        """
        errors: list[str] = []
        if not HERMES_GOOGLE_API_SCRIPT:
            errors.append(
                "HERMES_GOOGLE_API_SCRIPT is not configured. "
                "Set this to the path of the Hermes google_api.py "
                "on the supervisor's machine."
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
        range_override=GOOGLE_SHEETS_RANGE,
    )

    errors = config.validate()
    if errors:
        raise RuntimeError(
            "Google Sheets configuration errors:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    return config