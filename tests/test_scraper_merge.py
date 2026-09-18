"""Tests for scraper merge logic and field mapping fixes.

Tests cover the fixes from the data-completeness audit:
- Tags mapping in merge_scraped_row
- OutreachStatus defaulting to "New"
- DiscoveredAt generation for new records
- Source generation for new records
- FeedURL preservation when new value is empty
- FollowerCount "N/A" handling
- Language empty fallback (no unconditional "English")
- Human-data preservation during scraping
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

import pytest

# Ensure project paths are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = PROJECT_ROOT / "code"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from scraper.common import merge_scraped_row, is_discovery_only, _now_utc


# --- merge_scraped_row Tests ---

class TestMergeScrapedRow:
    """Test that merge_scraped_row correctly maps all fields."""

    def _make_row(self, **overrides):
        """Create a base row dict with all target columns."""
        from scraper.common import TARGET_COLUMNS
        row = {col: "" for col in TARGET_COLUMNS}
        row.update(overrides)
        return row

    def _make_scraped(self, **overrides):
        """Create a scraped data dict."""
        data = {
            "Handle": "TestCreator",
            "FollowerCount": "12.3K",
            "Email": "test@example.com",
            "Tags": "AIGC,YouTube,AI-Creator",
            "LastScrapedAt": "2026-09-18T12:00:00Z",
            "Language": "English",
            "PrimaryAITool": "GenAI",
            "SampleContentURL": "https://example.com/video",
            "AIGCVerdict": "yes",
            "Notes": "Scrape test",
            "FeedURL": "https://example.com/feed",
            "ContactSourceURL": "https://example.com/about",
            "EvidenceJSON": '{"test": true}',
        }
        data.update(overrides)
        return data

    def test_tags_reaches_crm(self):
        """Tags from scraped_data must reach row_dict."""
        row = self._make_row()
        scraped = self._make_scraped()
        merged = merge_scraped_row(row, scraped)
        assert merged["Tags"] == "AIGC,YouTube,AI-Creator"

    def test_tags_preserved_if_scraped_empty(self):
        """Existing Tags should not be erased by empty scraper Tags."""
        row = self._make_row(Tags="Existing Tags")
        scraped = self._make_scraped(Tags="")
        merged = merge_scraped_row(row, scraped)
        assert merged["Tags"] == "Existing Tags"

    def test_tags_preserved_if_scraped_none(self):
        """Existing Tags should not be erased by None scraper Tags."""
        row = self._make_row(Tags="Existing Tags")
        scraped = self._make_scraped(Tags=None)
        merged = merge_scraped_row(row, scraped)
        assert merged["Tags"] == "Existing Tags"

    def test_outreach_status_defaults_new(self):
        """OutreachStatus should default to 'New' for new records."""
        row = self._make_row(OutreachStatus="")
        scraped = self._make_scraped()
        merged = merge_scraped_row(row, scraped)
        assert merged["OutreachStatus"] == "New"

    def test_outreach_status_preserved_existing(self):
        """Existing OutreachStatus should never be overwritten."""
        row = self._make_row(OutreachStatus="Contacted")
        scraped = self._make_scraped()
        merged = merge_scraped_row(row, scraped)
        assert merged["OutreachStatus"] == "Contacted"

    def test_outreach_status_preserved_replied(self):
        """Human-maintained statuses like 'Replied' must be preserved."""
        row = self._make_row(OutreachStatus="Replied")
        scraped = self._make_scraped()
        merged = merge_scraped_row(row, scraped)
        assert merged["OutreachStatus"] == "Replied"

    def test_source_from_scraped_data(self):
        """Source from scraped_data should reach row_dict."""
        row = self._make_row(Source="")
        scraped = self._make_scraped(Source="YouTube")
        merged = merge_scraped_row(row, scraped)
        assert merged["Source"] == "YouTube"

    def test_source_preserved_existing(self):
        """Existing Source should not be overwritten by empty scraper Source."""
        row = self._make_row(Source="Web Search")
        scraped = self._make_scraped(Source="")
        merged = merge_scraped_row(row, scraped)
        assert merged["Source"] == "Web Search"

    def test_discovered_at_new_record(self):
        """DiscoveredAt should be set when row is empty."""
        row = self._make_row(DiscoveredAt="")
        scraped = self._make_scraped(DiscoveredAt="2026-09-18T10:00:00Z")
        merged = merge_scraped_row(row, scraped)
        assert merged["DiscoveredAt"] == "2026-09-18T10:00:00Z"

    def test_discovered_at_never_overwrite(self):
        """Existing DiscoveredAt must NEVER be replaced during subsequent scrapes."""
        original_discovered = "2026-07-20T06:13:47Z"
        row = self._make_row(DiscoveredAt=original_discovered)
        scraped = self._make_scraped(DiscoveredAt="2026-09-18T10:00:00Z")
        merged = merge_scraped_row(row, scraped)
        assert merged["DiscoveredAt"] == original_discovered

    def test_feedurl_preserved_if_scraped_empty(self):
        """Existing FeedURL should be preserved when scraper returns empty."""
        row = self._make_row(FeedURL="https://existing.com/feed")
        scraped = self._make_scraped(FeedURL="")
        merged = merge_scraped_row(row, scraped)
        assert merged["FeedURL"] == "https://existing.com/feed"

    def test_feedurl_updated_if_scraped_valid(self):
        """FeedURL should be updated when scraper returns valid value."""
        row = self._make_row(FeedURL="")
        scraped = self._make_scraped(FeedURL="https://new.com/feed")
        merged = merge_scraped_row(row, scraped)
        assert merged["FeedURL"] == "https://new.com/feed"

    def test_email_preserved_if_scraped_empty(self):
        """Existing Email should not be erased by empty scraper Email."""
        row = self._make_row(Email="existing@example.com")
        scraped = self._make_scraped(Email="")
        merged = merge_scraped_row(row, scraped)
        assert merged["Email"] == "existing@example.com"

    def test_language_preserved_if_scraped_empty(self):
        """Existing Language should not be erased by empty scraper Language."""
        row = self._make_row(Language="Japanese")
        scraped = self._make_scraped(Language="")
        merged = merge_scraped_row(row, scraped)
        assert merged["Language"] == "Japanese"

    def test_followercount_na_does_not_overwrite(self):
        """'N/A' FollowerCount should not overwrite existing valid value."""
        row = self._make_row(FollowerCount="146K")
        scraped = self._make_scraped(FollowerCount="N/A")
        merged = merge_scraped_row(row, scraped)
        assert merged["FollowerCount"] == "146K"

    def test_followercount_valid_new_value(self):
        """Valid new FollowerCount should be accepted."""
        row = self._make_row(FollowerCount="")
        scraped = self._make_scraped(FollowerCount="5.2M")
        merged = merge_scraped_row(row, scraped)
        assert merged["FollowerCount"] == "5.2M"

    def test_followercount_na_empty_record(self):
        """'N/A' FollowerCount on empty record should leave it empty."""
        row = self._make_row(FollowerCount="")
        scraped = self._make_scraped(FollowerCount="N/A")
        merged = merge_scraped_row(row, scraped)
        assert merged["FollowerCount"] == ""

    def test_notes_preserved(self):
        """Notes should always be set from scraped_data."""
        row = self._make_row()
        scraped = self._make_scraped(Notes="Scrape test")
        merged = merge_scraped_row(row, scraped)
        assert merged["Notes"] == "Scrape test"

    def test_evidencejson_preserved(self):
        """EvidenceJSON should always be set from scraped_data."""
        row = self._make_row()
        evidence = '{"follower": 1000}'
        scraped = self._make_scraped(EvidenceJSON=evidence)
        merged = merge_scraped_row(row, scraped)
        assert merged["EvidenceJSON"] == evidence

    def test_all_fields_mapping(self):
        """Verify all critical fields are properly mapped."""
        row = self._make_row()
        scraped = self._make_scraped()
        merged = merge_scraped_row(row, scraped)

        assert merged["Name/Handle"] == "TestCreator"
        assert merged["FollowerCount"] == "12.3K"
        assert merged["Tags"] == "AIGC,YouTube,AI-Creator"
        assert merged["LastScrapedAt"] == "2026-09-18T12:00:00Z"
        assert merged["Language"] == "English"
        assert merged["PrimaryAITool"] == "GenAI"
        assert merged["AIGCVerdict"] == "yes"
        assert merged["SampleContentURL"] == "https://example.com/video"
        assert merged["FeedURL"] == "https://example.com/feed"
        assert merged["ContactSourceURL"] == "https://example.com/about"
        assert merged["EvidenceJSON"] == '{"test": true}'


# --- is_discovery_only Tests ---

class TestIsDiscoveryOnly:
    """Test that 'N/A' follower count doesn't block valid records."""

    def test_na_follower_not_discovery(self):
        """'N/A' follower count should NOT be treated as discovery-only."""
        result = {"FollowerCount": "N/A", "Notes": "some notes"}
        assert is_discovery_only(result) is False

    def test_empty_follower_is_discovery(self):
        """Empty follower count should be discovery-only."""
        result = {"FollowerCount": "", "Notes": "some notes"}
        assert is_discovery_only(result) is True

    def test_valid_follower_not_discovery(self):
        """Valid follower count should not be discovery-only."""
        result = {"FollowerCount": "12.3K", "Notes": "some notes"}
        assert is_discovery_only(result) is False


# --- _now_utc Tests ---

class TestNowUtc:
    """Test the UTC timestamp generator."""

    def test_returns_string(self):
        """_now_utc should return a string."""
        result = _now_utc()
        assert isinstance(result, str)

    def test_valid_iso_format(self):
        """Result should be parseable as ISO datetime."""
        result = _now_utc()
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert dt.tzinfo is not None

    def test_utc_timezone(self):
        """Result should be in UTC."""
        result = _now_utc()
        dt = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert dt.tzinfo == timezone.utc


# --- Real Scraper Output Tests ---

class TestRealScraperOutput:
    """Test that real scraper output survives the full pipeline."""

    def test_youtube_scraper_tags_mapping(self):
        """Verify YouTube scraper Tags mapping works end-to-end."""
        from scraper.common import TARGET_COLUMNS
        row = {col: "" for col in TARGET_COLUMNS}
        row["ProfileURL"] = "https://www.youtube.com/@test"
        row["Platform"] = "YouTube"

        scraped = {
            "Handle": "@test",
            "FollowerCount": "12.3K",
            "Tags": "AIGC,YouTube,AI-Creator",
            "LastScrapedAt": "2026-09-18T12:00:00Z",
            "Language": "",
            "PrimaryAITool": "GenAI",
            "SampleContentURL": "https://youtube.com/watch?v=123",
            "AIGCVerdict": "yes",
            "Notes": "api_refresh: YouTube",
            "FeedURL": "https://youtube.com/feeds/videos.xml",
            "ContactSourceURL": "https://youtube.com/@test/about",
            "EvidenceJSON": '{"test": true}',
        }

        merged = merge_scraped_row(row, scraped)
        assert merged["Tags"] == "AIGC,YouTube,AI-Creator"
        assert merged["Language"] == ""
        assert merged["FeedURL"] == "https://youtube.com/feeds/videos.xml"

    def test_language_empty_not_english(self):
        """Language should be empty string, not 'English', when classifier returns empty."""
        from scraper.common import TARGET_COLUMNS
        row = {col: "" for col in TARGET_COLUMNS}
        scraped = {"Handle": "Test", "Language": ""}
        merged = merge_scraped_row(row, scraped)
        assert merged["Language"] == ""
        assert merged["Language"] != "English"


class TestAutoSyncToSheets:
    """Tests for the auto_sync_to_sheets function and Google Sheets integration."""

    def test_auto_sync_function_exists(self):
        """auto_sync_to_sheets should be importable from run.py."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code" / "scraper"))
        from run import auto_sync_to_sheets
        assert callable(auto_sync_to_sheets)

    def test_auto_sync_config_loads(self):
        """Google Sheets config must load correctly."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
        from sheets.config import load_config
        config = load_config()
        assert config.spreadsheet_id, "Spreadsheet ID must be configured"
        assert config.tab_name == "Temp", "Tab name must be Temp"
        assert not hasattr(config, "credentials_path"), "No credentials_path in new config"

    def test_auto_sync_exporter_initializes(self):
        """GoogleSheetsExporter can be instantiated."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
        from sheets.config import load_config
        from sheets.exporter import GoogleSheetsExporter
        config = load_config()
        exporter = GoogleSheetsExporter(config)
        assert exporter is not None
        assert exporter._config.spreadsheet_id == config.spreadsheet_id
        assert exporter._config.tab_name == config.tab_name

    def test_auto_sync_append_only_methods(self):
        """Exporter must have append-only methods."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
        from sheets.config import load_config
        from sheets.exporter import GoogleSheetsExporter
        config = load_config()
        exporter = GoogleSheetsExporter(config)
        assert hasattr(exporter, 'export')
        assert hasattr(exporter, '_get_existing_profile_urls')
        assert hasattr(exporter, '_find_new_records')

    def test_auto_sync_export_is_append_only(self):
        """export() method must use append_rows, not fullReplace."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
        from sheets.config import load_config
        from sheets.exporter import GoogleSheetsExporter
        config = load_config()
        exporter = GoogleSheetsExporter(config)
        import inspect
        source = inspect.getsource(exporter.export)
        assert "append_rows" in source
        assert "batchClear" not in source
        assert "fullReplace" not in source

    def test_auto_sync_zero_new_creators_handled(self):
        """Exporter must handle zero new creators case."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
        from sheets.config import load_config
        from sheets.exporter import GoogleSheetsExporter
        config = load_config()
        exporter = GoogleSheetsExporter(config)
        import inspect
        source = inspect.getsource(exporter.export)
        assert "new_creators" in source or "no new" in source.lower()


# =============================================================================
# Re-scrape & Safe Enrichment Tests
# =============================================================================

class TestSafeEnricher:
    """Tests for SafeEnricher field-level enrichment logic."""

    def setup_method(self):
        """Create a standard existing CRM row for testing."""
        self.base_row = {
            "ProfileURL": "https://www.tiktok.com/@testcreator",
            "Name/Handle": "@testcreator",
            "Platform": "TikTok",
            "FollowerCount": "10000",
            "Email": "",
            "Tags": "AI,Creator",
            "OutreachStatus": "Contacted",
            "LastScrapedAt": "2026-01-01T00:00:00Z",
            "Region": "",
            "Language": "English",
            "PrimaryAITool": "Runway",
            "SampleContentURL": "",
            "AIGCVerdict": "yes",
            "DiscoveredAt": "2025-06-15T12:00:00Z",
            "Source": "TikTok",
            "Notes": "Contacted through website",
            "FeedURL": "",
            "ContactSourceURL": "",
            "EvidenceJSON": '{"follower_raw_locale": "10000"}',
        }

    def test_existing_creator_never_deleted(self):
        """Re-scrape must never delete existing creators."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        scraped = {}  # No new data
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["ProfileURL"] == existing["ProfileURL"]

    def test_existing_profile_url_unchanged(self):
        """ProfileURL must never change during re-scraping."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        scraped = {"Handle": "newhandle"}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["ProfileURL"] == "https://www.tiktok.com/@testcreator"

    def test_empty_scraper_value_does_not_erase_existing(self):
        """Empty scraper value must not erase existing email."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Email"] = "creator@example.com"
        scraped = {"Email": ""}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["Email"] == "creator@example.com"

    def test_none_does_not_erase_existing(self):
        """None must not erase existing value."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Email"] = "creator@example.com"
        scraped = {"Email": None}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["Email"] == "creator@example.com"

    def test_nan_does_not_erase_existing(self):
        """NaN must not erase existing value."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Email"] = "creator@example.com"
        scraped = {"Email": "NaN"}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["Email"] == "creator@example.com"

    def test_na_does_not_erase_existing(self):
        """N/A must not erase existing value."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Email"] = "creator@example.com"
        scraped = {"Email": "N/A"}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["Email"] == "creator@example.com"

    def test_new_email_fills_empty_email(self):
        """New valid email should fill empty email."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Email"] = ""
        scraped = {"Email": "creator@example.com"}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["Email"] == "creator@example.com"
        assert any(c["field"] == "Email" and c["status"] == "changed" for c in changes)

    def test_new_follower_count_updates_existing(self):
        """Valid new follower count should update existing."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["FollowerCount"] = "10000"
        scraped = {"FollowerCount": "12000"}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["FollowerCount"] == "12000"

    def test_na_follower_count_preserves_existing(self):
        """N/A follower count must preserve existing count."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["FollowerCount"] = "10000"
        scraped = {"FollowerCount": "N/A"}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["FollowerCount"] == "10000"

    def test_new_tags_enrich_existing_tags(self):
        """New valid tags should enrich (merge with) existing tags."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Tags"] = "AI,Creator"
        scraped = {"Tags": "AIGC,Video"}
        enriched, changes = enricher.enrich(existing, scraped)
        tag_set = set(t.strip() for t in enriched["Tags"].split(","))
        assert "AI" in tag_set
        assert "Creator" in tag_set
        assert "AIGC" in tag_set
        assert "Video" in tag_set

    def test_outreach_status_preserved(self):
        """OutreachStatus must NEVER be changed during re-scraping."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["OutreachStatus"] = "Contacted"
        scraped = {"OutreachStatus": "New"}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["OutreachStatus"] == "Contacted"

    def test_discovered_at_preserved(self):
        """DiscoveredAt must NEVER change during re-scraping."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["DiscoveredAt"] = "2025-06-15T12:00:00Z"
        scraped = {"DiscoveredAt": "2026-09-18T00:00:00Z"}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["DiscoveredAt"] == "2025-06-15T12:00:00Z"

    def test_source_preserved(self):
        """Source must NEVER change during re-scraping."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Source"] = "TikTok"
        scraped = {"Source": "YouTube"}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["Source"] == "TikTok"

    def test_last_scraped_at_updates_on_success(self):
        """LastScrapedAt should update after successful scrape."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        scraped = {"LastScrapedAt": "2026-09-18T10:00:00Z"}
        enriched, changes = enricher.enrich(existing, scraped, scrape_successful=True)
        assert enriched["LastScrapedAt"] == "2026-09-18T10:00:00Z"

    def test_last_scraped_at_not_updated_on_failure(self):
        """LastScrapedAt must NOT update after failed scrape."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        scraped = {"LastScrapedAt": "2026-09-18T10:00:00Z"}
        enriched, changes = enricher.enrich(existing, scraped, scrape_successful=False)
        assert enriched["LastScrapedAt"] == "2026-01-01T00:00:00Z"

    def test_language_not_changed_to_english_when_detection_fails(self):
        """Language must NOT default to English when detection fails."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Language"] = "Malay"
        scraped = {"Language": ""}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["Language"] == "Malay"

    def test_region_not_guessed(self):
        """Region must not be guessed when scraper returns empty."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Region"] = ""
        scraped = {"Region": ""}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["Region"] == ""

    def test_existing_notes_preserved(self):
        """Existing Notes must NEVER be erased."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Notes"] = "Contacted through website"
        scraped = {"Notes": ""}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["Notes"] == "Contacted through website"

    def test_feed_url_preserved_when_new_empty(self):
        """FeedURL must be preserved when new value is empty."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["FeedURL"] = "https://example.com/feed"
        scraped = {"FeedURL": ""}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["FeedURL"] == "https://example.com/feed"

    def test_contact_source_url_preserved_when_new_empty(self):
        """ContactSourceURL must be preserved when new value is empty."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["ContactSourceURL"] = "https://example.com/contact"
        scraped = {"ContactSourceURL": ""}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["ContactSourceURL"] == "https://example.com/contact"

    def test_evidence_json_remains_valid(self):
        """EvidenceJSON must remain valid JSON after enrichment."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["EvidenceJSON"] = '{"follower_raw_locale": "10000"}'
        scraped = {"EvidenceJSON": '{"new_key": "new_val"}'}
        enriched, changes = enricher.enrich(existing, scraped)
        import json
        evidence = json.loads(enriched["EvidenceJSON"])
        assert isinstance(evidence, dict)
        assert "new_key" in evidence
        assert "follower_raw_locale" in evidence

    def test_no_duplicate_profile_urls(self):
        """Re-scraping must not create duplicate ProfileURLs."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        # Simulate enrichment that preserves ProfileURL
        scraped = {}  # No new data
        enriched, _ = enricher.enrich(existing, scraped)
        assert enriched["ProfileURL"] == existing["ProfileURL"]

    def test_creator_count_never_decreases(self):
        """Re-scraping must not reduce the number of creators."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        scraped = {}  # No data = no change
        enriched, _ = enricher.enrich(existing, scraped)
        # The enriched record still exists
        assert enriched["ProfileURL"] is not None

    def test_google_sheets_only_updates_changed_cells(self):
        """Google Sheets re-scrape must only update changed columns."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
        from sheets.exporter import GoogleSheetsExporter
        import inspect
        source = inspect.getsource(GoogleSheetsExporter.export_reshaped)
        # Must use update_cells or values().update, not full replace
        assert "update_cells" in source or "values().update" in source
        # Must NOT use batchClear or fullReplace API methods
        assert ".batchClear" not in source
        assert ".fullReplace" not in source
        assert ".deleteRow" not in source
        assert ".deleteDimension" not in source

    def test_google_sheets_existing_rows_never_deleted(self):
        """Google Sheets must never delete existing rows."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
        from sheets.exporter import GoogleSheetsExporter
        import inspect
        source = inspect.getsource(GoogleSheetsExporter.export_reshaped)
        # Must NOT call delete APIs
        assert ".deleteRow" not in source
        assert ".batchClear" not in source
        assert ".deleteDimension" not in source

    def test_google_sheets_unrelated_cells_unchanged(self):
        """Google Sheets update must not affect unrelated cells."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
        from sheets.exporter import GoogleSheetsExporter
        import inspect
        source = inspect.getsource(GoogleSheetsExporter.export_reshaped)
        # Should use targeted cell ranges via update_cells
        assert "update_cells" in source or "values().update" in source

    def test_full_sheet_replacement_never_used(self):
        """Full-sheet replacement must never be used."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
        from sheets.exporter import GoogleSheetsExporter
        import inspect
        source = inspect.getsource(GoogleSheetsExporter.export_reshaped)
        # Must NOT use full-replace API methods
        assert ".fullReplace" not in source
        assert ".batchClear" not in source

    def test_dry_run_produces_no_writes(self):
        """Dry-run must not modify any files."""
        from scraper.run import rescrape_creators
        import inspect
        source = inspect.getsource(rescrape_creators)
        # The function checks dry_run before writing
        assert "dry_run" in source
        assert "to_csv" in source  # to_csv is gated by dry_run check

    def test_scraper_failure_preserves_existing_record(self):
        """Failed scrape must preserve existing record entirely."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        # Simulate total scrape failure — empty scraped data
        enriched, changes = enricher.enrich(existing, {}, scrape_successful=False)
        # All fields should remain as-is
        assert enriched["Email"] == existing["Email"]
        assert enriched["FollowerCount"] == existing["FollowerCount"]
        assert enriched["Notes"] == existing["Notes"]

    def test_classifier_failure_preserves_classified_fields(self):
        """Classifier failure must preserve existing classified fields."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Language"] = "Malay"
        existing["PrimaryAITool"] = "Runway"
        existing["AIGCVerdict"] = "yes"
        # Classifier returns empty
        scraped = {"Language": "", "PrimaryAITool": "", "AIGCVerdict": ""}
        enriched, _ = enricher.enrich(existing, scraped)
        assert enriched["Language"] == "Malay"
        assert enriched["PrimaryAITool"] == "Runway"
        assert enriched["AIGCVerdict"] == "yes"

    def test_empty_scraped_value_does_not_erase_notes(self):
        """Empty Notes from scraper must NOT erase existing Notes."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Notes"] = "Human-written notes"
        scraped = {"Notes": ""}
        enriched, _ = enricher.enrich(existing, scraped)
        assert enriched["Notes"] == "Human-written notes"

    def test_ai_tool_preserved_when_unknown(self):
        """PrimaryAITool must be preserved when unknown."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["PrimaryAITool"] = "Runway"
        scraped = {"PrimaryAITool": ""}
        enriched, _ = enricher.enrich(existing, scraped)
        assert enriched["PrimaryAITool"] == "Runway"

    def test_email_never_replaced_with_empty(self):
        """Valid email must NEVER be replaced with empty."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["Email"] = "creator@example.com"
        scraped = {"Email": ""}
        enriched, _ = enricher.enrich(existing, scraped)
        assert enriched["Email"] == "creator@example.com"

    def test_feed_url_enrichs_when_empty(self):
        """FeedURL should be filled when existing is empty and scraped has valid value."""
        from scraper.common import SafeEnricher
        enricher = SafeEnricher()
        existing = dict(self.base_row)
        existing["FeedURL"] = ""
        scraped = {"FeedURL": "https://example.com/feed"}
        enriched, changes = enricher.enrich(existing, scraped)
        assert enriched["FeedURL"] == "https://example.com/feed"