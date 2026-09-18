"""Google Sheets API client for reading/writing spreadsheet data."""

import json
import sys
from pathlib import Path
from typing import Any

# Add code directory to path for importing sheets modules
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CODE_DIR = _PROJECT_ROOT / "code"
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetsClient:
    """Client for interacting with the Google Sheets API.

    Handles OAuth authentication using local credentials.json and token.json.
    All operations are one-way: writes CSV data to a spreadsheet tab.
    Does NOT read from or merge data from Google Sheets back into the system.
    """

    def __init__(self, spreadsheet_id: str, credentials_path: Path, token_path: Path):
        self._spreadsheet_id = spreadsheet_id
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._service = None

    def _get_credentials(self) -> Credentials:
        """Obtain valid credentials, refreshing or re-authenticating as needed."""
        credentials = None

        # Try to load existing token
        if self._token_path.exists():
            try:
                credentials = Credentials.from_authorized_user_file(
                    str(self._token_path), SCOPES
                )
            except Exception:
                credentials = None

        # Refresh if valid
        if credentials and credentials.valid:
            return credentials

        # Re-authenticate if expired
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                with open(self._token_path, "w") as token_file:
                    token_file.write(credentials.to_json())
                return credentials
            except Exception:
                pass

        # Full OAuth flow
        if not self._credentials_path.exists():
            raise RuntimeError(
                f"Credentials file not found: {self._credentials_path}\n"
                "1. Go to Google Cloud Console\n"
                "2. Create credentials -> OAuth Client ID -> Desktop app\n"
                "3. Download credentials.json and place it in the project root\n"
                "4. Run the export to start the authentication flow"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(self._credentials_path), SCOPES
        )
        credentials = flow.run_local_server(port=0)

        with open(self._token_path, "w") as token_file:
            token_file.write(credentials.to_json())

        return credentials

    def connect(self):
        """Authenticate and create the Google Sheets API service."""
        try:
            credentials = self._get_credentials()
            self._service = build("sheets", "v4", credentials=credentials)
        except HttpError as e:
            raise RuntimeError(f"Google Sheets API error during connection: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to authenticate with Google Sheets: {e}")

    @property
    def service(self):
        """Return the Google Sheets API service object."""
        if self._service is None:
            self.connect()
        return self._service

    def tab_exists(self, tab_name: str) -> bool:
        """Check if a sheet tab exists in the spreadsheet."""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self._spreadsheet_id
            ).execute()
            sheets = spreadsheet.get("sheets", [])
            return any(s.get("properties", {}).get("title") == tab_name for s in sheets)
        except HttpError as e:
            raise RuntimeError(f"Failed to check tabs: {e}")

    def write_range(self, range_name: str, values: list[list[Any]]) -> dict:
        """Write values to a range in the spreadsheet.

        Uses the Google Sheets API update endpoint to overwrite values
        in a specific range.
        """
        try:
            body = {"values": values}
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self._spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body,
            ).execute()
            return result
        except HttpError as e:
            raise RuntimeError(f"Failed to write to range {range_name}: {e}")

    def update_cells(self, range_name: str, values: list[list[Any]]) -> dict:
        """Update specific cells in the spreadsheet (column-level updates).

        For re-scrape: update only the changed cells of existing rows.
        Uses the same mechanism as write_range but semantically different.

        Args:
            range_name: A1 notation range (e.g., "'Temp'!B5:F5")
            values: 2D list of cell values to write.

        Returns:
            dict with update response.
        """
        try:
            body = {"values": values}
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self._spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body,
            ).execute()
            return result
        except HttpError as e:
            raise RuntimeError(f"Failed to update cells in {range_name}: {e}")

    def append_rows(self, range_name: str, values: list[list[Any]]) -> dict:
        """Append values to a range in the spreadsheet.

        Uses the Google Sheets API append endpoint to add rows
        after the last existing data row.
        """
        try:
            body = {"values": values}
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self._spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body,
            ).execute()
            return result
        except HttpError as e:
            raise RuntimeError(f"Failed to append rows to {range_name}: {e}")

    def read_range(self, range_name: str) -> list[list[Any]]:
        """Read values from a range in the spreadsheet."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self._spreadsheet_id,
                range=range_name,
            ).execute()
            values = result.get("values", [])
            return values
        except HttpError as e:
            raise RuntimeError(f"Failed to read range {range_name}: {e}")

    def close(self):
        """Release the API service connection."""
        self._service = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


__all__ = ["GoogleSheetsClient", "SCOPES"]