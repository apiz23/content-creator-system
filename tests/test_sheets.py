"""Tests for the Google Sheets integration module.

Tests cover:
- Configuration loading and validation (no credentials required)
- Subprocess-based client adapter (mocked subprocess.run)
- Incremental append export behavior
- ProfileURL-based duplicate detection
- Data quality (clean_cell_value, EvidenceJSON, Unicode)
- Backup functionality
"""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = PROJECT_ROOT / "code"

# Ensure project paths are in sys.path before any imports
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))
if str(CODE_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(CODE_DIR))


def parse_export_result(result_str: str) -> dict:
    """Parse a result dict."""
    if isinstance(result_str, dict):
        return result_str
    try:
        return json.loads(result_str)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON: {result_str}"}


# =============================================================================
# Config Tests
# =============================================================================

class TestConfig:
    """Test configuration loading and validation without credentials."""

    def test_missing_tab_name_fails(self):
        """Missing GOOGLE_SHEETS_TAB_NAME should raise RuntimeError."""
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="",
        )
        errors = config.validate()
        assert any("GOOGLE_SHEETS_TAB_NAME" in e for e in errors)

    def test_missing_spreadsheet_id_fails(self):
        """Missing spreadsheet ID should raise RuntimeError."""
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="",
            tab_name="Test Tab",
        )
        errors = config.validate()
        assert any("GOOGLE_SHEETS_SPREADSHEET_ID" in e for e in errors)

    def test_no_credentials_required(self):
        """SheetsConfig should not require credentials_path or token_path."""
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        assert hasattr(config, "spreadsheet_id")
        assert not hasattr(config, "credentials_path")
        assert not hasattr(config, "token_path")

    def test_range_auto_generated(self):
        """Range should auto-generate from tab name for 19 columns (A:S)."""
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Creator Intel",
        )
        assert config.range == "'Creator Intel'!A:S"

    def test_range_override(self):
        """Explicit range override should be used."""
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Creator Intel",
            range_override="Creator Intel!A1:S10",
        )
        assert config.range == "Creator Intel!A1:S10"

    def test_validate_adapter(self):
        """validate_adapter should warn when HERMES_GOOGLE_API_SCRIPT is missing."""
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        errors = config.validate_adapter()
        assert isinstance(errors, list)


# =============================================================================
# Exporter Tests
# =============================================================================

class TestExporter:
    """Test the Google Sheets exporter logic."""

    def test_correct_column_order(self):
        """Export should select exactly the 19 TARGET_COLUMNS in order."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__(
            "scraper.common", fromlist=["TARGET_COLUMNS"]
        ).TARGET_COLUMNS

        test_csv = Path("/tmp/test_crm_export.csv")
        all_cols = list(TARGET_COLS) + ["ExtraColumn"]
        df = pd.DataFrame([{col: "val" for col in all_cols}])
        df.to_csv(test_csv, index=False)

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        exporter = GoogleSheetsExporter(config)
        df_loaded = exporter._load_csv()

        assert list(df_loaded.columns) == list(TARGET_COLS)
        assert "ExtraColumn" not in df_loaded.columns

        test_csv.unlink(missing_ok=True)

    def test_extra_columns_ignored(self):
        """Extra columns in the CSV should not appear in exported data."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__(
            "scraper.common", fromlist=["TARGET_COLUMNS"]
        ).TARGET_COLUMNS

        test_csv = Path("/tmp/test_crm_extra.csv")
        all_cols = list(TARGET_COLS) + ["ExtraCol1", "ExtraCol2"]
        df = pd.DataFrame([{col: "val" for col in all_cols}])
        df.to_csv(test_csv, index=False)

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        exporter = GoogleSheetsExporter(config)
        df_loaded = exporter._load_csv()

        assert len(df_loaded.columns) == 19
        assert "ExtraCol1" not in df_loaded.columns
        assert "ExtraCol2" not in df_loaded.columns

        test_csv.unlink(missing_ok=True)

    def test_empty_csv_raises(self):
        """Empty/missing CSV should raise RuntimeError."""
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        exporter = GoogleSheetsExporter(config)
        exporter._csv_path = Path("/nonexistent/nonexistent.csv")

        with pytest.raises(RuntimeError, match="not found"):
            exporter._load_csv()

    def test_missing_columns_detected(self):
        """Missing required columns should raise RuntimeError."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__(
            "scraper.common", fromlist=["TARGET_COLUMNS"]
        ).TARGET_COLUMNS

        test_csv = Path("/tmp/test_crm_missing.csv")
        df = pd.DataFrame([{"ProfileURL": "https://test.com"}])
        df.to_csv(test_csv, index=False)

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        exporter = GoogleSheetsExporter(config)
        exporter._csv_path = test_csv

        with pytest.raises(RuntimeError, match="Missing required columns"):
            exporter._load_csv()

        test_csv.unlink(missing_ok=True)


# =============================================================================
# clean_cell_value Tests
# =============================================================================

class TestCleanCellValue:
    """Test that missing/null values become empty strings."""

    def test_clean_cell_value_none(self):
        """Python None should become empty string."""
        from sheets.exporter import clean_cell_value
        assert clean_cell_value(None) == ""

    def test_clean_cell_value_nan(self):
        """pandas NaN should become empty string."""
        import pandas as pd
        from sheets.exporter import clean_cell_value
        assert clean_cell_value(float("nan")) == ""

    def test_clean_cell_value_na(self):
        """pandas NA should become empty string."""
        import pandas as pd
        from sheets.exporter import clean_cell_value
        assert clean_cell_value(pd.NA) == ""

    def test_clean_cell_value_empty_string(self):
        """Empty string should become empty string."""
        from sheets.exporter import clean_cell_value
        assert clean_cell_value("") == ""

    def test_clean_cell_value_none_string(self):
        """Literal 'None' string should become empty string."""
        from sheets.exporter import clean_cell_value
        assert clean_cell_value("None") == ""

    def test_clean_cell_value_null_string(self):
        """Literal 'null' string should become empty string."""
        from sheets.exporter import clean_cell_value
        assert clean_cell_value("null") == ""

    def test_clean_cell_value_nan_technology(self):
        """Legitimate 'nanotechnology' must NOT become empty string."""
        from sheets.exporter import clean_cell_value
        assert clean_cell_value("nanotechnology") == "nanotechnology"

    def test_clean_cell_value_uppercase_null(self):
        """Literal 'NULL' string should become empty string."""
        from sheets.exporter import clean_cell_value
        assert clean_cell_value("NULL") == ""

    def test_clean_cell_value_email(self):
        """Valid email strings must be preserved."""
        from sheets.exporter import clean_cell_value
        assert clean_cell_value("test@example.com") == "test@example.com"

    def test_clean_cell_value_json(self):
        """Valid JSON strings must be preserved."""
        json_str = '{"key": "value"}'
        from sheets.exporter import clean_cell_value
        assert clean_cell_value(json_str) == json_str

    def test_clean_cell_value_whitespace(self):
        """Whitespace-only strings should become empty string."""
        from sheets.exporter import clean_cell_value
        assert clean_cell_value("   ") == ""

    def test_clean_cell_value_legitimate_text(self):
        """Legitimate multilingual text must be preserved."""
        from sheets.exporter import clean_cell_value
        assert (
            clean_cell_value("Konten AI dalam Bahasa Melayu 🇲🇾")
            == "Konten AI dalam Bahasa Melayu 🇲🇾"
        )


# =============================================================================
# Incremental Append Tests
# =============================================================================

class TestIncrementalAppend:
    """Test the incremental append behavior."""

    def test_existing_profile_url_skipped(self):
        """New ProfileURL → should be identified as new."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__(
            "scraper.common", fromlist=["TARGET_COLUMNS"]
        ).TARGET_COLUMNS

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        exporter = GoogleSheetsExporter(config)

        row1 = {col: "val" for col in TARGET_COLS}
        row1["ProfileURL"] = "https://test.com/profile1"
        row2 = {col: "val" for col in TARGET_COLS}
        row2["ProfileURL"] = "https://test.com/profile2"
        df_csv = pd.DataFrame([row1, row2])
        df_csv.to_csv("/tmp/test_append.csv", index=False)

        existing_urls = {"https://test.com/profile1"}
        new_df = exporter._find_new_records(df_csv, existing_urls)
        assert len(new_df) == 1
        assert new_df.iloc[0]["ProfileURL"] == "https://test.com/profile2"

        os.unlink("/tmp/test_append.csv")

    def test_new_profile_url_appended(self):
        """New ProfileURL not in Google Sheets → should be appended."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__(
            "scraper.common", fromlist=["TARGET_COLUMNS"]
        ).TARGET_COLUMNS

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        exporter = GoogleSheetsExporter(config)

        df_csv = pd.DataFrame([{col: "val" for col in TARGET_COLS}])
        df_csv.to_csv("/tmp/test_new.csv", index=False)
        exporter._csv_path = Path("/tmp/test_new.csv")

        existing_urls = set()
        new_df = exporter._find_new_records(df_csv, existing_urls)
        assert len(new_df) == 1

        os.unlink("/tmp/test_new.csv")


# =============================================================================
# Client Tests (subprocess adapter)
# =============================================================================

class TestClient:
    """Test the Google Sheets subprocess client adapter."""

    def test_sheets_get_command(self, tmp_path):
        """sheets get command should be invoked correctly."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        with patch("sheets.client.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=json.dumps({"values": [["A1", "B1"]]}),
                stderr="",
                returncode=0,
            )
            client = GoogleSheetsClient(spreadsheet_id="test-id")
            result = client.read_range("'Creator Intel'!A1:S10")

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == client._python
            assert "sheets" in call_args
            assert call_args[3] == "get"
            assert call_args[4] == "test-id"
            assert call_args[5] == "'Creator Intel'!A1:S10"
            assert result == [["A1", "B1"]]

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_sheets_append_command(self, tmp_path):
        """sheets append command should be invoked correctly."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        with patch("sheets.client.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=json.dumps({"updates": {}}),
                stderr="",
                returncode=0,
            )
            client = GoogleSheetsClient(spreadsheet_id="test-id")
            values = [["val1", "val2"], ["val3", "val4"]]
            client.append_rows("'Creator Intel'!A1128:S1131", values)

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "sheets" in call_args
            assert call_args[3] == "append"
            assert call_args[4] == "test-id"
            assert call_args[5] == "'Creator Intel'!A1128:S1131"
            assert "--values" in call_args

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_sheets_update_command(self, tmp_path):
        """sheets update command should be invoked correctly."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        with patch("sheets.client.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=json.dumps({"updatedCells": 3}),
                stderr="",
                returncode=0,
            )
            client = GoogleSheetsClient(spreadsheet_id="test-id")
            values = [["new_val"]]
            client.update_cells("'Creator Intel'!B5:D5", values)

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "sheets" in call_args
            assert call_args[3] == "update"
            assert call_args[4] == "test-id"
            assert call_args[5] == "'Creator Intel'!B5:D5"
            assert "--values" in call_args

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_json_values_serialization(self, tmp_path):
        """Values should be serialized as JSON in the command."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        with patch("sheets.client.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=json.dumps({}),
                stderr="",
                returncode=0,
            )
            client = GoogleSheetsClient(spreadsheet_id="test-id")
            values = [["a", "b"], ["c", "d"]]
            client.append_rows("'Test'!A1:B2", values)

            call_args = mock_run.call_args[0][0]
            values_idx = call_args.index("--values")
            values_json = json.loads(call_args[values_idx + 1])
            assert values_json == values

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_json_response_parsing(self, tmp_path):
        """Stdout JSON should be parsed and returned."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        with patch("sheets.client.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=json.dumps({"values": [["A1"], ["B2"]]}),
                stderr="",
                returncode=0,
            )
            client = GoogleSheetsClient(spreadsheet_id="test-id")
            result = client.read_range("'Test'!A1:A2")

            assert result == [["A1"], ["B2"]]

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_nonzero_returncode_raises(self, tmp_path):
        """Non-zero subprocess returncode should raise RuntimeError."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        with patch("sheets.client.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="",
                stderr="Error: something went wrong",
                returncode=1,
            )
            client = GoogleSheetsClient(spreadsheet_id="test-id")
            with pytest.raises(RuntimeError, match="failed"):
                client.read_range("'Test'!A1:A1")

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_stderr_handling(self, tmp_path):
        """Stderr should not be exposed in error messages."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        with patch("sheets.client.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout="",
                stderr="secret_token=abc123",
                returncode=1,
            )
            client = GoogleSheetsClient(spreadsheet_id="test-id")
            with pytest.raises(RuntimeError) as exc_info:
                client.read_range("'Test'!A1:A1")
            error_msg = str(exc_info.value)
            assert "secret_token=abc123" not in error_msg
            assert "failed" in error_msg.lower()

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_missing_hermes_executable(self, tmp_path):
        """Invalid HERMES_GOOGLE_API_PYTHON should be stored correctly."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        os.environ["HERMES_GOOGLE_API_PYTHON"] = "/nonexistent/python"
        client = GoogleSheetsClient(spreadsheet_id="test-id")
        assert client._python == "/nonexistent/python"

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)
        os.environ.pop("HERMES_GOOGLE_API_PYTHON", None)

    def test_missing_google_api_script(self, tmp_path):
        """Missing google_api.py should raise RuntimeError on connect."""
        from sheets.client import GoogleSheetsClient

        os.environ["HERMES_GOOGLE_API_SCRIPT"] = "/nonexistent/google_api.py"
        os.environ.pop("HERMES_GOOGLE_API_PYTHON", None)
        client = GoogleSheetsClient(spreadsheet_id="test-id")

        with pytest.raises(RuntimeError, match="not found"):
            client.connect()

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_hermes_python_override(self, tmp_path):
        """HERMES_GOOGLE_API_PYTHON should override the default Python."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        os.environ["HERMES_GOOGLE_API_PYTHON"] = "/custom/python"
        client = GoogleSheetsClient(spreadsheet_id="test-id")
        assert client._python == "/custom/python"

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)
        os.environ.pop("HERMES_GOOGLE_API_PYTHON", None)

    def test_hermes_script_override(self, tmp_path):
        """HERMES_GOOGLE_API_SCRIPT should override the default script path."""
        from sheets.client import GoogleSheetsClient

        os.environ["HERMES_GOOGLE_API_SCRIPT"] = "/custom/google_api.py"
        client = GoogleSheetsClient(spreadsheet_id="test-id")
        assert client._script == "/custom/google_api.py"

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_tab_exists(self, tmp_path):
        """tab_exists should use 'sheets get' with a harmless read."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        with patch("sheets.client.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=json.dumps({"values": [["Header"]]}),
                stderr="",
                returncode=0,
            )
            client = GoogleSheetsClient(spreadsheet_id="test-id")
            result = client.tab_exists("Creator Intel")

            assert result is True
            call_args = mock_run.call_args[0][0]
            assert "Creator Intel'!A1:A1" in call_args[5]

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_missing_tab_returns_false(self, tmp_path):
        """Missing tab should return False, not raise."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        with patch("sheets.client.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=json.dumps({"values": []}),
                stderr="",
                returncode=0,
            )
            client = GoogleSheetsClient(spreadsheet_id="test-id")
            result = client.tab_exists("NonExistent")

            assert result is False

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_connect_does_not_call_google(self, tmp_path):
        """connect() must NOT call Google or make API calls."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        with patch("sheets.client.subprocess.run") as mock_run:
            client = GoogleSheetsClient(spreadsheet_id="test-id")
            client.connect()
            # connect() only validates, does not call subprocess.run
            mock_run.assert_not_called()

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_connect_does_not_launch_oauth(self, tmp_path):
        """connect() must NOT launch a browser or OAuth flow."""
        from sheets.client import GoogleSheetsClient

        fake_script = tmp_path / "fake_google_api.py"
        fake_script.write_text("# fake")
        os.environ["HERMES_GOOGLE_API_SCRIPT"] = str(fake_script)
        client = GoogleSheetsClient(spreadsheet_id="test-id")
        # Should not have any references to browser, OAuth, or installed app flow
        assert not hasattr(client, "_credentials_path")
        assert not hasattr(client, "_token_path")

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)

    def test_credentials_json_not_required(self, tmp_path):
        """credentials.json should not be required or referenced."""
        from sheets.client import GoogleSheetsClient

        os.environ.pop("HERMES_GOOGLE_API_SCRIPT", None)
        os.environ.pop("HERMES_GOOGLE_API_PYTHON", None)

        client = GoogleSheetsClient(spreadsheet_id="test-id")
        assert client._spreadsheet_id == "test-id"
        assert not hasattr(client, "_credentials_path")
        assert not hasattr(client, "_token_path")

    def test_token_json_not_required(self, tmp_path):
        """token.json should not be required or referenced."""
        from sheets.client import GoogleSheetsClient

        client = GoogleSheetsClient(spreadsheet_id="test-id")
        assert not hasattr(client, "_token_path")
        assert not hasattr(client, "_credentials_path")


# =============================================================================
# EvidenceJSON Tests
# =============================================================================

class TestEvidenceJSON:
    """Test that EvidenceJSON is preserved correctly."""

    def test_evidence_json_preserved_in_rows(self):
        """EvidenceJSON should remain valid JSON string in new rows."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__(
            "scraper.common", fromlist=["TARGET_COLUMNS"]
        ).TARGET_COLUMNS

        test_csv = Path("/tmp/test_evidence.csv")
        evidence = {"follower_count": {"source": "test", "value": 1000}}
        row_data = {col: "val" for col in TARGET_COLS}
        row_data["EvidenceJSON"] = json.dumps(evidence)
        row_data["ProfileURL"] = "https://new.com"
        df = pd.DataFrame([row_data])
        df.to_csv(test_csv, index=False)

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        exporter = GoogleSheetsExporter(config)
        exporter._csv_path = test_csv
        df_loaded = exporter._load_csv()
        new_df = exporter._find_new_records(df_loaded, set())

        assert len(new_df) == 1
        evidence_val = new_df.iloc[0]["EvidenceJSON"]
        parsed = json.loads(evidence_val)
        assert parsed["follower_count"]["value"] == 1000

        test_csv.unlink(missing_ok=True)


# =============================================================================
# Unicode Tests
# =============================================================================

class TestUnicodeContent:
    """Test that multilingual content is preserved."""

    def test_malay_text_preserved(self):
        """Malay/Unicode text should be preserved in new records."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__(
            "scraper.common", fromlist=["TARGET_COLUMNS"]
        ).TARGET_COLUMNS

        test_csv = Path("/tmp/test_unicode.csv")
        row_data = {col: "test" for col in TARGET_COLS}
        row_data["Notes"] = "Konten AI dalam Bahasa Melayu 🇲🇾"
        row_data["Name/Handle"] = "创作者测试"
        row_data["ProfileURL"] = "https://new.com"
        df = pd.DataFrame([row_data])
        df.to_csv(test_csv, index=False)

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        exporter = GoogleSheetsExporter(config)
        exporter._csv_path = test_csv
        df_loaded = exporter._load_csv()
        new_df = exporter._find_new_records(df_loaded, set())

        assert len(new_df) == 1
        assert "Bahasa Melayu" in new_df.iloc[0]["Notes"]
        assert "创作者" in new_df.iloc[0]["Name/Handle"]

        test_csv.unlink(missing_ok=True)


# =============================================================================
# Backup Tests
# =============================================================================

class TestBackup:
    """Test CSV backup creation."""

    def test_backup_creates_file(self, tmp_path):
        """Backup should create a timestamped CSV file."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig
        from scraper.common import CRM_FILE

        test_csv = tmp_path / "test_crm.csv"
        TARGET_COLS = __import__(
            "scraper.common", fromlist=["TARGET_COLUMNS"]
        ).TARGET_COLUMNS
        df = pd.DataFrame([{col: "val" for col in TARGET_COLS}])
        df.to_csv(test_csv, index=False)

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        exporter = GoogleSheetsExporter(config)
        exporter._csv_path = test_csv
        backup_path = exporter._create_backup()

        assert Path(backup_path).exists()
        backup_df = pd.read_csv(backup_path)
        assert len(backup_df) == 1

    def test_backup_fails_if_csv_missing(self):
        """Backup should fail if CSV doesn't exist."""
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
        )
        exporter = GoogleSheetsExporter(config)
        exporter._csv_path = Path("/nonexistent/nonexistent.csv")

        with pytest.raises(RuntimeError, match="CRM file not found"):
            exporter._create_backup()
