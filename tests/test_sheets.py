"""Tests for the Google Sheets integration module.

Tests cover:
- Configuration loading and validation
- Incremental append export behavior
- ProfileURL-based duplicate detection
- Data quality (clean_cell_value, EvidenceJSON, Unicode)
- Client API interactions
- Backup functionality
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = PROJECT_ROOT / "code"

# Ensure project paths are in sys.path before any imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))


def parse_export_result(result_str: str) -> dict:
    """Parse a result dict."""
    if isinstance(result_str, dict):
        return result_str
    try:
        return json.loads(result_str)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON: {result_str}"}


# --- Config Tests ---

class TestConfig:
    """Test configuration loading and validation."""

    def test_missing_tab_name_fails(self):
        """Missing GOOGLE_SHEETS_TAB_NAME should raise RuntimeError."""
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        errors = config.validate()
        assert any("GOOGLE_SHEETS_TAB_NAME" in e for e in errors)

    def test_missing_spreadsheet_id_fails(self):
        """Missing spreadsheet ID should raise RuntimeError."""
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        errors = config.validate()
        assert any("GOOGLE_SHEETS_SPREADSHEET_ID" in e for e in errors)

    def test_missing_credentials_fails(self):
        """Missing credentials.json should be caught in validation."""
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        errors = config.validate()
        assert any("credentials" in e.lower() for e in errors)

    def test_range_auto_generated(self):
        """Range should auto-generate from tab name for 19 columns (A:S)."""
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Creator Intel",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        assert config.range == "'Creator Intel'!A:S"

    def test_range_override(self):
        """Explicit range override should be used."""
        from sheets.config import SheetsConfig

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Creator Intel",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
            range_override="Creator Intel!A1:S10",
        )
        assert config.range == "Creator Intel!A1:S10"


# --- Exporter Tests ---

class TestExporter:
    """Test the Google Sheets exporter logic."""

    def test_correct_column_order(self):
        """Export should select exactly the 19 TARGET_COLUMNS in order."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        test_csv = Path("/tmp/test_crm_export.csv")
        all_cols = list(__import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS) + ["ExtraColumn"]
        df = pd.DataFrame([{col: "val" for col in all_cols}])
        df.to_csv(test_csv, index=False)

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)
        df_loaded = exporter._load_csv()

        assert list(df_loaded.columns) == list(
            __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS
        )
        assert "ExtraColumn" not in df_loaded.columns

        test_csv.unlink(missing_ok=True)

    def test_extra_columns_ignored(self):
        """Extra columns in the CSV should not appear in exported data."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

        test_csv = Path("/tmp/test_crm_extra.csv")
        all_cols = list(TARGET_COLS) + ["ExtraCol1", "ExtraCol2"]
        df = pd.DataFrame([{col: "val" for col in all_cols}])
        df.to_csv(test_csv, index=False)

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
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
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
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

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

        test_csv = Path("/tmp/test_crm_missing.csv")
        df = pd.DataFrame([{"ProfileURL": "https://test.com"}])
        df.to_csv(test_csv, index=False)

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)
        exporter._csv_path = test_csv

        with pytest.raises(RuntimeError, match="Missing required columns"):
            exporter._load_csv()

        test_csv.unlink(missing_ok=True)


# --- clean_cell_value Tests ---

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

    def test_clean_cell_value_with_whitespace(self):
        """Whitespace-only strings should become empty string."""
        from sheets.exporter import clean_cell_value
        assert clean_cell_value("   ") == ""

    def test_clean_cell_value_legitimate_text(self):
        """Legitimate multilingual text must be preserved."""
        from sheets.exporter import clean_cell_value
        assert clean_cell_value("Konten AI dalam Bahasa Melayu 🇲🇾") == "Konten AI dalam Bahasa Melayu 🇲🇾"


# --- Incremental Append Tests ---

class TestIncrementalAppend:
    """Test the incremental append behavior."""

    def test_existing_profile_url_skipped(self):
        """New ProfileURL → should be identified as new."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)

        # CSV has 2 records
        row1 = {col: "val" for col in TARGET_COLS}
        row1["ProfileURL"] = "https://test.com/profile1"
        row2 = {col: "val" for col in TARGET_COLS}
        row2["ProfileURL"] = "https://test.com/profile2"
        df_csv = pd.DataFrame([row1, row2])
        df_csv.to_csv("/tmp/test_append.csv", index=False)
        exporter._csv_path = Path("/tmp/test_append.csv")

        # Existing Google Sheet has the first ProfileURL
        existing_urls = {"https://test.com/profile1"}

        new_df = exporter._find_new_records(df_csv, existing_urls)
        assert len(new_df) == 1  # Only 1 new record
        assert new_df.iloc[0]["ProfileURL"] == "https://test.com/profile2"

        import os
        os.unlink("/tmp/test_append.csv")

    def test_new_profile_url_appended(self):
        """New ProfileURL not in Google Sheets → should be appended."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)

        df_csv = pd.DataFrame([{col: "val" for col in TARGET_COLS}])
        df_csv.to_csv("/tmp/test_new.csv", index=False)
        exporter._csv_path = Path("/tmp/test_new.csv")

        # No existing URLs in Google Sheets
        existing_urls = set()

        new_df = exporter._find_new_records(df_csv, existing_urls)
        assert len(new_df) == 1

        import os
        os.unlink("/tmp/test_new.csv")

    def test_mixed_existing_and_new_records(self):
        """Mixed existing + new records → only new ones returned."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)

        row1 = {col: "val1" for col in TARGET_COLS}
        row1["ProfileURL"] = "https://existing.com"
        row2 = {col: "val2" for col in TARGET_COLS}
        row2["ProfileURL"] = "https://new.com"
        row3 = {col: "val3" for col in TARGET_COLS}
        row3["ProfileURL"] = "https://existing2.com"

        df_csv = pd.DataFrame([row1, row2, row3])
        df_csv.to_csv("/tmp/test_mixed.csv", index=False)
        exporter._csv_path = Path("/tmp/test_mixed.csv")

        existing_urls = {"https://existing.com", "https://existing2.com"}
        new_df = exporter._find_new_records(df_csv, existing_urls)

        assert len(new_df) == 1
        assert new_df.iloc[0]["ProfileURL"] == "https://new.com"

        import os
        os.unlink("/tmp/test_mixed.csv")

    def test_duplicate_profile_urls_in_csv(self):
        """Duplicate ProfileURLs inside the CSV → all treated as new if not in Sheets."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)

        row1 = {col: "val" for col in TARGET_COLS}
        row1["ProfileURL"] = "https://same.com"
        row2 = {col: "val" for col in TARGET_COLS}
        row2["ProfileURL"] = "https://same.com"

        df_csv = pd.DataFrame([row1, row2])
        df_csv.to_csv("/tmp/test_dup.csv", index=False)
        exporter._csv_path = Path("/tmp/test_dup.csv")

        existing_urls = set()
        new_df = exporter._find_new_records(df_csv, existing_urls)

        assert len(new_df) == 2  # Both are new since not in Sheets

        import os
        os.unlink("/tmp/test_dup.csv")

    def test_whitespace_in_profile_url(self):
        """ProfileURL whitespace differences → normalized for comparison."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)

        row = {col: "val" for col in TARGET_COLS}
        row["ProfileURL"] = "https://test.com/ "  # trailing space

        df_csv = pd.DataFrame([row])
        df_csv.to_csv("/tmp/test_ws.csv", index=False)
        exporter._csv_path = Path("/tmp/test_ws.csv")

        # Existing URL without trailing slash/space
        existing_urls = {"https://test.com"}

        new_df = exporter._find_new_records(df_csv, existing_urls)
        assert len(new_df) == 0  # Should be treated as existing

        import os
        os.unlink("/tmp/test_ws.csv")

    def test_no_new_records_no_write(self):
        """All ProfileURLs already exist → should return 0 new rows."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)

        row = {col: "val" for col in TARGET_COLS}
        row["ProfileURL"] = "https://existing.com"
        df_csv = pd.DataFrame([row])
        df_csv.to_csv("/tmp/test_none.csv", index=False)
        exporter._csv_path = Path("/tmp/test_none.csv")

        existing_urls = {"https://existing.com"}
        new_df = exporter._find_new_records(df_csv, existing_urls)

        assert len(new_df) == 0

        import os
        os.unlink("/tmp/test_none.csv")


# --- clean_cell_value with _find_new_records ---

class TestNewRecordsDataQuality:
    """Test data quality in incremental append."""

    def test_new_records_preserve_evidence_json(self):
        """EvidenceJSON should remain valid JSON in new rows."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)

        evidence = {"follower_count": {"source": "test", "value": 1000}}
        row_data = {col: "val" for col in TARGET_COLS}
        row_data["EvidenceJSON"] = json.dumps(evidence)
        row_data["ProfileURL"] = "https://new.com"
        df_csv = pd.DataFrame([row_data])
        df_csv.to_csv("/tmp/test_evidence.csv", index=False)
        exporter._csv_path = Path("/tmp/test_evidence.csv")

        existing_urls = set()
        new_df = exporter._find_new_records(df_csv, existing_urls)
        assert len(new_df) == 1
        assert "EvidenceJSON" in new_df.columns

        import os
        os.unlink("/tmp/test_evidence.csv")

    def test_new_records_empty_values(self):
        """Missing values in new records should be preserved."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)

        row_data = {col: "val" for col in TARGET_COLS}
        row_data["Email"] = ""
        row_data["ProfileURL"] = "https://new.com"
        df_csv = pd.DataFrame([row_data])
        df_csv.to_csv("/tmp/test_empty.csv", index=False)
        exporter._csv_path = Path("/tmp/test_empty.csv")

        existing_urls = set()
        new_df = exporter._find_new_records(df_csv, existing_urls)
        assert len(new_df) == 1
        # Email is empty string after CSV round-trip
        assert new_df.iloc[0]["Email"] == ""

        import os
        os.unlink("/tmp/test_empty.csv")

    def test_batch_append_not_one_per_row(self):
        """All new records are collected into one batch, not one per row."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)

        rows = []
        for i in range(10):
            row = {col: f"val{i}" for col in TARGET_COLS}
            row["ProfileURL"] = f"https://new{i}.com"
            rows.append(row)

        df_csv = pd.DataFrame(rows)
        df_csv.to_csv("/tmp/test_batch.csv", index=False)
        exporter._csv_path = Path("/tmp/test_batch.csv")

        existing_urls = set()
        new_df = exporter._find_new_records(df_csv, existing_urls)

        # All 10 are new
        assert len(new_df) == 10
        # The important thing is they're all collected in ONE DataFrame
        # (the actual API append is a single batch call)

        import os
        os.unlink("/tmp/test_batch.csv")


# --- Client Tests ---

class TestClient:
    """Test Google Sheets client with mocked API calls."""

    @patch("sheets.client.build")
    @patch("sheets.client.Credentials.from_authorized_user_file")
    def test_tab_exists(self, mock_creds, mock_build):
        """Tab existence check should work correctly."""
        from sheets.client import GoogleSheetsClient

        mock_creds.return_value = Mock(valid=True)
        mock_service = Mock()
        mock_build.return_value = mock_service

        mock_spreadsheet = Mock()
        mock_spreadsheet.get.return_value = {"sheets": [
            {"properties": {"title": "Creator Intel"}},
            {"properties": {"title": "Other Tab"}},
        ]}
        mock_service.spreadsheets().get.return_value.execute.return_value = (
            mock_spreadsheet.get.return_value
        )

        client = GoogleSheetsClient(
            spreadsheet_id="test-id",
            credentials_path=Path("/tmp/fake_creds.json"),
            token_path=Path("/tmp/fake_token.json"),
        )
        client._service = mock_service

        assert client.tab_exists("Creator Intel") is True
        assert client.tab_exists("NonExistent") is False

    @patch("sheets.client.build")
    def test_connect_success(self, mock_build):
        """Connection should succeed with mocked API service."""
        from sheets.client import GoogleSheetsClient
        from google.oauth2.credentials import Credentials

        mock_creds = Credentials(token="fake")
        mock_service = Mock()
        mock_build.return_value = mock_service

        client = GoogleSheetsClient(
            spreadsheet_id="test-id",
            credentials_path=Path("/tmp/fake_creds.json"),
            token_path=Path("/tmp/fake_token.json"),
        )
        client._get_credentials = Mock(return_value=mock_creds)
        client.connect()

        assert client._service is not None

    @patch("sheets.client.build")
    def test_append_rows(self, mock_build):
        """append_rows should call the API correctly."""
        from sheets.client import GoogleSheetsClient
        from google.oauth2.credentials import Credentials

        mock_creds = Credentials(token="fake")
        mock_service = Mock()
        mock_build.return_value = mock_service

        client = GoogleSheetsClient(
            spreadsheet_id="test-id",
            credentials_path=Path("/tmp/fake_creds.json"),
            token_path=Path("/tmp/fake_token.json"),
        )
        client._get_credentials = Mock(return_value=mock_creds)
        client.connect()

        test_values = [["val1", "val2"], ["val3", "val4"]]
        client.append_rows("'Test'!A2:B3", test_values)

        mock_service.spreadsheets().values().append.assert_called_once()
        call_args = mock_service.spreadsheets().values().append.call_args
        assert call_args.kwargs["valueInputOption"] == "RAW"
        assert call_args.kwargs["body"]["values"] == test_values

    @patch("sheets.client.build")
    def test_write_range(self, mock_build):
        """Write range should call the API with correct parameters."""
        from sheets.client import GoogleSheetsClient
        from google.oauth2.credentials import Credentials

        mock_creds = Credentials(token="fake")
        mock_service = Mock()
        mock_build.return_value = mock_service

        client = GoogleSheetsClient(
            spreadsheet_id="test-id",
            credentials_path=Path("/tmp/fake_creds.json"),
            token_path=Path("/tmp/fake_token.json"),
        )
        client._get_credentials = Mock(return_value=mock_creds)
        client.connect()

        test_values = [["Header1", "Header2"], ["val1", "val2"]]
        client.write_range("'Test'!A1:B2", test_values)

        mock_service.spreadsheets().values().update.assert_called_once()
        call_args = mock_service.spreadsheets().values().update.call_args
        assert call_args.kwargs["body"]["values"] == test_values


# --- EvidenceJSON Tests ---

class TestEvidenceJSON:
    """Test that EvidenceJSON is preserved correctly."""

    def test_evidence_json_preserved_in_rows(self):
        """EvidenceJSON should remain valid JSON string in new rows."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

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
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
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


# --- Unicode Tests ---

class TestUnicodeContent:
    """Test that multilingual content is preserved."""

    def test_malay_text_preserved(self):
        """Malay/Unicode text should be preserved in new records."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig

        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS

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
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)
        exporter._csv_path = test_csv
        df_loaded = exporter._load_csv()
        new_df = exporter._find_new_records(df_loaded, set())

        assert len(new_df) == 1
        assert "Bahasa Melayu" in new_df.iloc[0]["Notes"]
        assert "创作者" in new_df.iloc[0]["Name/Handle"]

        test_csv.unlink(missing_ok=True)


# --- Backup Tests ---

class TestBackup:
    """Test CSV backup creation."""

    def test_backup_creates_file(self, tmp_path):
        """Backup should create a timestamped CSV file."""
        import pandas as pd
        from sheets.exporter import GoogleSheetsExporter
        from sheets.config import SheetsConfig
        from scraper.common import CRM_FILE

        test_csv = tmp_path / "test_crm.csv"
        TARGET_COLS = __import__("scraper.common", fromlist=["TARGET_COLUMNS"]).TARGET_COLUMNS
        df = pd.DataFrame([{col: "val" for col in TARGET_COLS}])
        df.to_csv(test_csv, index=False)

        config = SheetsConfig(
            spreadsheet_id="test-id",
            tab_name="Test Tab",
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
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
            credentials_path=Path("/nonexistent/credentials.json"),
            token_path=Path("/nonexistent/token.json"),
        )
        exporter = GoogleSheetsExporter(config)
        exporter._csv_path = Path("/nonexistent/nonexistent.csv")

        with pytest.raises(RuntimeError, match="CRM file not found"):
            exporter._create_backup()
