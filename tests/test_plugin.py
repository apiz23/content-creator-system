"""Tests for the Content Creator System plugin."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ensure project root is first in path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_tool_result(result_str: str) -> dict:
    """Parse a tool handler's JSON string result."""
    try:
        return json.loads(result_str)
    except json.JSONDecodeError:
        return {"error": f"Invalid JSON: {result_str}"}


class TestPluginManifest:
    """Test that the plugin manifest is valid."""

    def test_plugin_yaml_exists(self):
        assert (PROJECT_ROOT / "plugin.yaml").exists()

    def test_plugin_yaml_has_name(self):
        with open(PROJECT_ROOT / "plugin.yaml") as f:
            content = f.read()
        assert "name: content-creator-system" in content

    def test_plugin_yaml_has_tools(self):
        with open(PROJECT_ROOT / "plugin.yaml") as f:
            content = f.read()
        assert "creator_scrape" in content
        assert "creator_batch_scrape" in content
        assert "creator_validate" in content


class TestSchemas:
    """Test that tool schemas are valid."""

    def test_creator_scrape_schema(self):
        import schemas
        assert schemas.CREATOR_SCRAPE["name"] == "creator_scrape"
        assert "url" in schemas.CREATOR_SCRAPE["parameters"]["properties"]

    def test_creator_batch_scrape_schema(self):
        import schemas
        assert schemas.CREATOR_BATCH_SCRAPE["name"] == "creator_batch_scrape"
        assert "platform" in schemas.CREATOR_BATCH_SCRAPE["parameters"]["properties"]
        assert "source" in schemas.CREATOR_BATCH_SCRAPE["parameters"]["properties"]

    def test_creator_validate_schema(self):
        import schemas
        assert schemas.CREATOR_VALIDATE["name"] == "creator_validate"


class TestCreatorScrape:
    """Test creator_scrape tool handler."""

    def test_missing_url_returns_error(self):
        import tools
        result = parse_tool_result(tools.creator_scrape({}))
        assert result["success"] is False
        assert "error" in result

    def test_empty_url_returns_error(self):
        import tools
        result = parse_tool_result(tools.creator_scrape({"url": "  "}))
        assert result["success"] is False
        assert "error" in result


class TestCreatorBatchScrape:
    """Test creator_batch_scrape tool handler."""

    def test_invalid_platform_returns_error(self, monkeypatch):
        import tools
        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 1
                stdout = ""
                stderr = "Invalid platform"
            return MockResult()
        monkeypatch.setattr("subprocess.run", mock_run)
        result = parse_tool_result(tools.creator_batch_scrape({"platform": "xyz"}))
        assert result["success"] is False
        assert "error" in result

    def test_source_crm_default(self, monkeypatch):
        """Default source should be 'crm'."""
        import tools
        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 0
                stdout = "[+] Processed: 1 | Successful: 1 | Failed: 0"
                stderr = ""
            return MockResult()
        monkeypatch.setattr("subprocess.run", mock_run)
        result = parse_tool_result(tools.creator_batch_scrape({
            "platform": "tiktok",
            "limit": 1,
        }))
        assert result["success"] is True
        assert result["source"] == "crm"

    def test_source_crm_with_backup(self, monkeypatch):
        """CRM source should create backup before scraping."""
        import tools
        backup_created = False
        
        def mock_backup(*args, **kwargs):
            nonlocal backup_created
            backup_created = True
            return "/tmp/test_backup.csv"
        
        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 0
                stdout = "[+] Processed: 1 | Successful: 1 | Failed: 0"
                stderr = ""
            return MockResult()
        
        monkeypatch.setattr("subprocess.run", mock_run)
        # Mock _backup_crm in tools module
        monkeypatch.setattr(tools, "_backup_crm", mock_backup)
        result = parse_tool_result(tools.creator_batch_scrape({
            "source": "crm",
            "platform": "tiktok",
            "limit": 1,
        }))
        assert result["success"] is True
        assert backup_created is True

    def test_source_input_uses_input_file(self, monkeypatch):
        """source='input' should use input_file path."""
        import tools
        def mock_run(*args, **kwargs):
            class MockResult:
                returncode = 0
                stdout = "[+] Processed: 1 | Successful: 1 | Failed: 0"
                stderr = ""
            return MockResult()
        monkeypatch.setattr("subprocess.run", mock_run)
        result = parse_tool_result(tools.creator_batch_scrape({
            "source": "input",
            "input_file": "data/input/input_channels.csv",
            "limit": 1,
        }))
        assert result["success"] is True
        assert result["source"] == "input"

    def test_path_traversal_rejected(self):
        import tools
        result = parse_tool_result(tools.creator_batch_scrape({
            "source": "input",
            "input_file": "/etc/passwd",
        }))
        assert result["success"] is False
        assert "must be within project directory" in result["error"]

    def test_outside_project_path_rejected(self):
        import tools
        result = parse_tool_result(tools.creator_batch_scrape({
            "source": "input",
            "input_file": "../secret.txt",
        }))
        assert result["success"] is False
        assert "must be within project directory" in result["error"]

    def test_nonexistent_file_rejected(self):
        import tools
        result = parse_tool_result(tools.creator_batch_scrape({
            "source": "input",
            "input_file": "data/nonexistent.csv",
        }))
        assert result["success"] is False
        assert "not found" in result["error"]


class TestCreatorValidate:
    """Test creator_validate tool handler."""

    def test_validate_master_crm(self):
        import tools
        result = parse_tool_result(tools.creator_validate({}))
        assert result["success"] is True
        assert "total_rows" in result
        assert result["total_rows"] > 0


class TestRegister:
    """Test plugin registration."""

    def test_register_function_exists(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("plugin_init", PROJECT_ROOT / "__init__.py")
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        assert callable(mod.register)


class TestBackupCrm:
    """Test backup_crm utility."""

    def test_backup_creates_file(self, tmp_path):
        """Test that backup_crm creates a timestamped backup."""
        import pandas as pd
        import sys
        scraper_path = str(PROJECT_ROOT / "code" / "scraper")
        if scraper_path not in sys.path:
            sys.path.insert(0, scraper_path)
        from common import backup_crm
        
        # Create a test CRM
        test_crm = tmp_path / "test_crm.csv"
        df = pd.DataFrame([{
            "ProfileURL": "https://example.com",
            "Name/Handle": "@test",
            "Platform": "tiktok",
        }])
        df.to_csv(test_crm, index=False)
        
        # Create backup
        backup_path = backup_crm(test_crm)
        
        assert Path(backup_path).exists()
        assert "test_crm" in backup_path
        
        # Verify backup content matches
        backup_df = pd.read_csv(backup_path)
        assert len(backup_df) == 1
        assert backup_df.iloc[0]["ProfileURL"] == "https://example.com"

    def test_backup_fails_if_crm_missing(self, tmp_path):
        """Test that backup_crm raises error if CRM doesn't exist."""
        import sys
        scraper_path = str(PROJECT_ROOT / "code" / "scraper")
        if scraper_path not in sys.path:
            sys.path.insert(0, scraper_path)
        from common import backup_crm
        
        with pytest.raises(RuntimeError, match="CRM file not found"):
            backup_crm(tmp_path / "nonexistent.csv")

    def test_backup_creates_unique_filenames(self, tmp_path):
        """Test that multiple backups get unique filenames."""
        import pandas as pd
        import sys
        scraper_path = str(PROJECT_ROOT / "code" / "scraper")
        if scraper_path not in sys.path:
            sys.path.insert(0, scraper_path)
        from common import backup_crm
        
        test_crm = tmp_path / "test_crm.csv"
        df = pd.DataFrame([{"ProfileURL": "https://example.com"}])
        df.to_csv(test_crm, index=False)
        
        backup1 = backup_crm(test_crm)
        backup2 = backup_crm(test_crm)
        
        assert backup1 != backup2
        assert Path(backup1).exists()
        assert Path(backup2).exists()
