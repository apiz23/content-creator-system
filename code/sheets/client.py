"""Subprocess-based Google Sheets client.

Uses the existing Hermes google_api.py wrapper as a subprocess
to perform all Google Sheets operations.

No OAuth, no browser, no local credentials.
All authentication is managed by the Hermes installation.

Commands:
    sheets get SHEET_ID RANGE
    sheets append SHEET_ID RANGE --values JSON
    sheets update SHEET_ID RANGE --values JSON
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Add project root and code directory to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CODE_DIR = _PROJECT_ROOT / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from sheets.config import SheetsConfig


class GoogleSheetsClient:
    """Client for interacting with Google Sheets via the Hermes CLI.

    The Hermes google_api.py wrapper handles all OAuth authentication
    internally. This client only invokes the wrapper as a subprocess
    and parses the JSON output.

    No credentials are stored or required by this repository.
    """

    def __init__(self, spreadsheet_id: str, config: SheetsConfig = None):
        self._spreadsheet_id = spreadsheet_id
        self._config = config
        self._python = self._get_hermes_python()
        self._script = self._get_hermes_script()

    def _get_hermes_python(self) -> str:
        """Get the Python executable for the Hermes google_api.py wrapper.

        Uses HERMES_GOOGLE_API_PYTHON if set, otherwise defaults
        to the current Python interpreter.
        """
        import os
        return os.environ.get(
            "HERMES_GOOGLE_API_PYTHON", sys.executable
        )

    def _get_hermes_script(self) -> str:
        """Get the path to the Hermes google_api.py script.

        Uses HERMES_GOOGLE_API_SCRIPT if set, otherwise defaults
        to the expected path on the supervisor's machine.
        """
        import os
        script = os.environ.get("HERMES_GOOGLE_API_SCRIPT", "")
        if script:
            return script
        # Default expected path on supervisor's Mac Mini.
        # Not validated during import — only checked at runtime.
        return str(
            Path.home() / ".hermes" / "skills" / "productivity"
            / "google-workspace" / "scripts" / "google_api.py"
        )

    def _validate_adapter(self):
        """Validate that the Hermes google_api.py adapter is available.

        Raises:
            RuntimeError: If the configured script cannot be found.
        """
        if not Path(self._script).exists():
            raise RuntimeError(
                f"Hermes google_api.py not found at: {self._script}\n"
                "Configure HERMES_GOOGLE_API_SCRIPT to point to the "
                "existing Hermes installation, or install Hermes "
                "on this machine."
            )

    def _invoke(self, *args: str) -> dict:
        """Invoke the Hermes google_api.py wrapper as a subprocess.

        Args:
            *args: Command arguments to pass to sheets command.

        Returns:
            Parsed JSON response from stdout.

        Raises:
            RuntimeError: If the subprocess fails or returns invalid JSON.
        """
        self._validate_adapter()

        cmd = [self._python, self._script, "sheets"] + list(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Hermes Python executable not found: {self._python}. "
                "Configure HERMES_GOOGLE_API_PYTHON."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "Hermes google_api.py timed out. "
                "Check the Google Sheets connection."
            )

        if result.returncode != 0:
            # Do not expose secrets in error messages
            stderr = result.stderr.strip() if result.stderr else "Unknown error"
            raise RuntimeError(
                f"Google Sheets operation failed (exit code {result.returncode}). "
                "Check the configured Hermes installation."
            )

        # Parse stdout as JSON
        try:
            return json.loads(result.stdout.strip()) if result.stdout.strip() else {}
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Invalid JSON response from Hermes google_api.py: {e}"
            )

    def connect(self):
        """Validate configuration and adapter setup.

        Does NOT authenticate, launch a browser, or call Google.
        Only checks that the Hermes wrapper is configured and available.
        """
        self._validate_adapter()

    def close(self):
        """No-op. The subprocess adapter does not maintain a persistent connection."""
        pass

    def tab_exists(self, tab_name: str) -> bool:
        """Check if a sheet tab exists.

        Uses a harmless read of a single cell.

        Args:
            tab_name: The name of the tab to check.

        Returns:
            True if the tab exists, False otherwise.
        """
        try:
            result = self._invoke(
                "get", self._spreadsheet_id, f"'{tab_name}'!A1:A1"
            )
            # Handle both list format (direct JSON) and dict format
            if isinstance(result, list):
                values = result
            elif isinstance(result, dict):
                values = result.get("values", [])
            else:
                return False
            return len(values) > 0 and len(values[0]) > 0
        except Exception:
            return False

    def read_range(self, range_name: str) -> list[list[Any]]:
        """Read values from a range in the spreadsheet.

        Args:
            range_name: A1 notation range (e.g., "'Creator Intel'!A1:S100").

        Returns:
            List of rows, where each row is a list of cell values.
            First row is the header.
        """
        result = self._invoke("get", self._spreadsheet_id, range_name)
        # Handle both list format (direct JSON) and dict format
        if isinstance(result, list):
            values = result
        elif isinstance(result, dict):
            values = result.get("values", [])
        else:
            values = []
        return values

    def append_rows(self, range_name: str, values: list[list[Any]]) -> dict:
        """Append rows to a range in the spreadsheet.

        Args:
            range_name: A1 notation range (e.g., "'Creator Intel'!A1128:S1132").
            values: 2D list of cell values to append.

        Returns:
            dict with the append response.
        """
        values_json = json.dumps(values)
        return self._invoke(
            "append", self._spreadsheet_id, range_name, "--values", values_json
        )

    def update_cells(self, range_name: str, values: list[list[Any]]) -> dict:
        """Update specific cells in the spreadsheet.

        Args:
            range_name: A1 notation range (e.g., "'Creator Intel'!B5:D5").
            values: 2D list of cell values to write.

        Returns:
            dict with the update response.
        """
        values_json = json.dumps(values)
        return self._invoke(
            "update", self._spreadsheet_id, range_name, "--values", values_json
        )


__all__ = ["GoogleSheetsClient"]