---
name: creator-research
description: Use for creator discovery, scraping, and CRM management.
version: 2.0.0
author: Hafizuddin
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Creator Research, Scraping, AI Content, Social Media]
    related_skills: [cronjob]
---

# Creator Research System

A safety-first workflow for building and maintaining a research dataset of publicly available creator information.

## When to Use

Load this skill when the user asks to discover or find new creators, scrape a platform (TikTok, Instagram, Facebook, LinkedIn, Reddit, Threads, YouTube, Vimeo, Civitai), refresh creator data, merge results into the Master CRM, or run any creator research workflow. Trigger on phrases like "find creators," "scrape TikTok," "refresh CRM data," or "run research pipeline."

## Quick Reference

| Tool | Description |
|------|-------------|
| `creator_scrape` | Scrape one public creator profile URL. Returns structured data. |
| `creator_batch_scrape` | Rescrape creators from Master CRM. Supports platform filter and limit. Always creates backup. |
| `creator_validate` | Validate Master CRM data quality (duplicates, schema, integrity). |

## Procedure

### Architecture

```
Hermes Agent
    ↓
web_search (native) → /creator-discover (slash command)
    ↓
creator_scrape (plugin tool) — scrape one creator
creator_batch_scrape (plugin tool) — rescrape from Master CRM
    ↓
creator_validate (plugin tool)
    ↓
data/Creator-Intel-CRM-List.csv (SINGLE SOURCE OF TRUTH)
```

### Master CRM

**File:** `data/Creator-Intel-CRM-List.csv`

- Every creator appears exactly once (deduped by ProfileURL, case-insensitive)
- Updated (never replaced) when new scrape data arrives
- 19 columns: ProfileURL, Name/Handle, Platform, FollowerCount, Email, Tags, OutreachStatus, LastScrapedAt, Region, Language, PrimaryAITool, SampleContentURL, AIGCVerdict, DiscoveredAt, Source, Notes, FeedURL, ContactSourceURL, EvidenceJSON

**Legacy file:** `data/input/input_channels.csv` is the active scraping queue. Use it for filtering platform scrapers. Do NOT delete it.

### Google Sheets Sync — USER CONFIRMATION REQUIRED

**CRITICAL RULE: Google Sheets synchronization NEVER happens automatically without explicit user confirmation.**

After Creator Research finishes and the CSV has been updated:

1. Validate the CSV.
2. Create the CSV backup.
3. Report what was discovered/added.
4. ASK THE USER whether they want to sync the new records to Google Sheets.
5. STOP and WAIT for the user's explicit confirmation.

Only if the user explicitly confirms should Hermes run:

```bash
python3 run_sheets.py export
```

Do NOT interpret "continue", "done", "okay", "looks good", or "research complete" as permission to sync. The default behavior is:

RESEARCH → CSV → BACKUP → ASK USER → WAIT

NOT: RESEARCH → CSV → BACKUP → GOOGLE SHEETS

### Incremental Append Mode

The Google Sheets exporter uses **incremental append only** — it never clears or rewrites existing rows:

1. Reads existing ProfileURLs from the configured Google Sheet tab
2. Compares against CRM ProfileURLs (normalized: strip whitespace, lowercase, remove trailing slash)
3. Appends ONLY new records in a single batch API call
4. Existing rows are NEVER deleted, replaced, reordered, or modified
5. If no new records: reports "No new creators to export" and makes no changes

### Empty Value Handling

- `clean_cell_value()` converts null/NaN/None/empty strings → genuinely empty cell `""`
- Legitimate text like "nanotechnology" is preserved unchanged

### Platform Name Casing

- Platform names must be properly cased: YouTube, TikTok, Facebook, Instagram, LinkedIn, Reddit, Threads, Vimeo, Civitai
- `code/` cannot be a Python package (stdlib `code` conflict) — use `run_sheets.py` or `sys.path.insert`
- Never use `python -m code.sheets` — use `python3 run_sheets.py`

### Google Sheets: Hermes Subprocess Adapter (NEW)

This repository does NOT manage Google OAuth credentials.
Google Sheets operations go through the existing Hermes CLI as a subprocess.

- **No credentials.json or token.json** — never stored in this repository
- **Hermes google_api.py** is invoked via `subprocess.run()` with `sheets get/append/update` commands
- **Configuration**: `GOOGLE_SHEETS_SPREADSHEET_ID`, `GOOGLE_SHEETS_TAB_NAME`, `GOOGLE_SHEETS_RANGE` in `.env`
- **Optional**: `HERMES_GOOGLE_API_PYTHON` and `HERMES_GOOGLE_API_SCRIPT` point to the Hermes installation on the supervisor's machine
- **Fails clearly** if Hermes google_api.py is not found — not a silent failure

```text
Creator Research / Scraper
          |
          v
    Hermes google_api.py (subprocess)
          |
          v
    Hermes-managed OAuth (on supervisor's machine)
          |
          v
    Google Sheets
```

See the `sheets-export` skill for full details on the Google Sheets export workflow.

### Credentials

- **This repository does NOT use credentials.json or token.json**
- Google Sheets auth is handled by the Hermes installation on the supervisor's Mac Mini
- On the supervisor's machine, Hermes provides: `$HERMES_HOME/google_token.json`, `$HERMES_HOME/google_client_secret.json`, `$HERMES_HOME/skills/productivity/google-workspace/scripts/google_api.py`

### Re-Scrape & Safe Data Enrichment

Re-scraping existing CRM creators for data enrichment (NOT replacement). Uses field-level enrichment — new valid data updates fields, empty/failed values NEVER erase existing data.

Commands:
```bash
python3 code/scraper/run.py rescrape --source csv --limit 5 --no-sync
python3 run_sheets.py rescrape --source csv --limit 5 --no-sync
python3 code/scraper/run.py rescrape --source sheets --dry-run --limit 10
```

Flags: `--source`, `--limit`, `--offset`, `--dry-run`, `--no-sync`, `--model-provider`, `--model-name`

### Key Re-Scrape Safety Rules

1. **Immutable fields NEVER change:** ProfileURL, DiscoveredAt, Source, OutreachStatus
2. **FollowerCount updates only if scraped value is valid/non-empty**
3. **Tags merge (dedup) when scraped value is valid**
4. **Language empty string when unknown — never "English"**
5. **Failed scrapes preserve all existing data** (no empty/null/NaN/N/A overwrites)
6. **LastScrapedAt updates only after successful scrape**
7. **Google Sheets column-level update only** — never `batchClear`, `fullReplace`, `deleteRow`
8. **`--no-sync` flag**: Skips Google Sheets sync entirely for controlled testing
9. **Zero new creators → zero append writes**

### Import Pattern for `code/` directory

The `code/` directory is NOT a Python package. Use `sys.path.insert` for imports:
```python
import sys
from pathlib import Path
PROJECT_ROOT = Path.cwd()
CODE_DIR = PROJECT_ROOT / "code"
sys.path.insert(0, str(CODE_DIR))
from scraper.run import rescrape_creators
```

## Backup Rules

Every operation that modifies the Master CRM creates a backup first:
- Location: `data/backups/Creator-Intel-CRM-List_YYYYMMDD_HHMMSS.csv`
- If backup creation fails, the operation aborts
- Backups are never overwritten (unique timestamps)
- Previous backups preserved

### Discovery Workflow

#### Natural Language (Recommended)

1. User: "Find 10 AI TikTok creators"
2. Hermes calls `web_search` with appropriate query
3. Hermes extracts candidate profile URLs from results
4. Hermes deduplicates against Master CRM (by ProfileURL)
5. Hermes calls `creator_scrape` for each new URL
6. Hermes calls `creator_validate` to confirm data quality

#### Slash Command
```
/creator-discover platform:tiktok keywords:"AI video" count:10
/creator-discover platform:instagram keywords:"AI art" count:5
/creator-discover platform:youtube keywords:"machine learning" count:20
```

### Before Every Scrape

1. Record current CRM row count: `wc -l data/Creator-Intel-CRM-List.csv`
2. Create backup: `python3 -c "from common import backup_crm; backup_crm()"`
3. Verify backup exists before proceeding

### Running Scrapers

#### Single Profile (Recommended)
```bash
source .venv/bin/activate
python3 code/scraper/run.py --url "https://www.tiktok.com/@example" --limit 1
```

#### Batch Scrape
```bash
source .venv/bin/activate
python3 code/scraper/run.py --input data/input/civitai_input.csv
```

#### Platform-Specific
```bash
source .venv/bin/activate
python3 code/scraper/civitai.py --limit 5
python3 code/scraper/reddit.py --limit 5
```

#### Important: Do NOT call platform scrapers directly for CRM merges
- Platform scrapers write to `data/output/<platform>_scraped_output.csv` — they do NOT merge to CRM
- Only `run.py --url` and `run.py --input` handle CRM merge
- `--platform` mode does NOT merge to CRM

### After Scraping

1. Verify CRM row count matches or increased — NEVER decreased
2. Check output CSV for errors
3. Update README.md row count

### CRM Merge Rules

- `merge_to_crm()` takes a single dict — updates existing or appends new
- `merge_results_to_crm()` takes a DataFrame — batch merge
- ProfileURL matching is case-insensitive + trailing-slash normalized
- Never bypass these functions with manual CSV writes

### Output Formatting (Every Scrape)

1. **Follower normalization** — K/M/B notation (e.g. 4812 → 4.8K)
2. **Bio cleanup** — strip platform UI chrome (Malay, cookie banners)
3. **Locale** — en-US browser context for all Playwright scrapers
4. **Link resolution** — decode redirect URLs to canonical profile URLs
5. **EvidenceJSON** — must be valid RFC 8259 JSON

## Verification

Before declaring any step complete, confirm:

- **Backup created:** Timestamped backup file exists at `data/backups/` before any CRM write
- **CRM row count preserved or increased:** Re-read CRM from disk after merge; count must equal before_count + appended − deleted
- **CRM row count never decreased:** If count drops below before_count, abort and restore from backup immediately
- **No duplicates:** Search CRM for duplicate ProfileURLs after merge
- **Schema intact:** Column count and order unchanged (19 columns, same sequence)
- **EvidenceJSON valid:** Every EvidenceJSON field parses as RFC 8259 JSON (no Python dict syntax)
- **ProfileURLs sanitized:** No tracking params (utm_*, fbclid, si, ref) in any ProfileURL
- **Platform casing canonical:** All platform values match canonical casing (TikTok, Facebook, Instagram, LinkedIn, Reddit, Threads, YouTube, Vimeo, Civitai)
- **README row count updated:** If CRM changed, README.md line reflects new count

## Re-Scrape & Safe Data Enrichment

Re-scraping existing CRM creators for data enrichment (NOT replacement). Uses field-level enrichment — new valid data updates fields, empty/failed values NEVER erase existing data.

### Commands

```bash
python3 code/scraper/run.py rescrape --source csv --limit 5 --no-sync
python3 run_sheets.py rescrape --source csv --limit 5 --no-sync
python3 code/scraper/run.py rescrape --source sheets --dry-run --limit 10
```

### Flags
- `--source csv|sheets|auto` — source of re-scrape queue
- `--limit N` — max creators to re-scrape
- `--offset N` — offset for batching
- `--dry-run` — preview changes without writing
- `--no-sync` — skip Google Sheets sync after re-scrape
- `--model-provider` / `--model-name` — AI classifier overrides

### SafeEnricher — Field-Level Enrichment Rules

| Field | Behavior |
|---|---|
| **ProfileURL** | NEVER changed — identity key |
| **DiscoveredAt** | NEVER overwritten — preserved from first add |
| **Source** | NEVER overwritten — preserved from first add |
| **OutreachStatus** | NEVER overwritten — human-maintained |
| **Email** | Only fills empty; never replaces existing |
| **Notes** | Preserved; never overwritten with empty |
| **FollowerCount** | Updated only if scraped value is valid/non-empty |
| **Tags** | Merged (dedup) when scraped value is valid |
| **Language** | Only fills empty; empty string when unknown |
| **PrimaryAITool** | Only fills empty; never replaces existing |
| **FeedURL** | Preserved when scraper returns empty |
| **SampleContentURL** | Preserved when scraper returns empty |
| **ContactSourceURL** | Preserved when scraper returns empty |
| **EvidenceJSON** | Updated with new data; valid RFC 8259 JSON |
| **LastScrapedAt** | Updated only after successful scrape |

### Failed Scrape Safety

When a scraper fails (404, timeout, bot wall):
- The existing CRM record is FULLY preserved
- No fields are cleared, emptied, or replaced with "N/A"
- The failed creator is listed in the re-scrape report under "Failed creators"
- Backup is still created before the merge attempt

### Google Sheets Safety (Re-Scrape)

- **New creators**: APPEND ONLY — never overwrite existing rows
- **Existing creators**: Column-level updates only via `update_cells()` — never `batchClear`, `fullReplace`, or `deleteRow`
- **Zero new creators**: Zero append writes
- **`--no-sync` flag**: Skips Google Sheets sync entirely

### Import Pattern for `code/` directory

The `code/` directory is NOT a Python package. Use `sys.path.insert` for imports:
```python
import sys
from pathlib import Path
PROJECT_ROOT = Path.cwd()
CODE_DIR = PROJECT_ROOT / "code"
sys.path.insert(0, str(CODE_DIR))
from scraper.run import rescrape_creators
```

### Helper Functions

- `is_val_empty(val)` — checks None, "", "None", "N/A", "nan", float NaN
- `_now_utc()` — current UTC ISO timestamp
- `normalize_scraped_result(result)` — normalizes follower count, cleans UI text, resolves URLs
- `SafeEnricher.enriches(existing_row, scraped_data, scrape_successful)` — returns (enriched_row, change_report)

### Re-Scrape Testing

```bash
# Dry-run to preview changes
python3 code/scraper/run.py rescrape --source csv --limit 5 --dry-run --no-sync

# Verify invariants after re-scrape
python3 -c "
import pandas as pd
crm = pd.read_csv('data/Creator-Intel-CRM-List.csv')
assert len(crm) == 1127  # No deletions
assert crm['ProfileURL'].duplicated().sum() == 0  # No duplicates
assert list(crm.columns) == ['ProfileURL', 'Name/Handle', ...]  # 19 columns
"
```

See `references/scraper-pipeline-map.md` for the complete re-scrape data flow and field mapping.

## Pitfalls

- **YouTube yt-dlp 404s**: Some channels return 404 — failed scrapes preserve existing data, check `Failed creators` in re-scrape report
- **`code/` is not a package**: Use `sys.path.insert(0, str(Path.cwd() / 'code'))` before importing `scraper.run`
- **Google Sheets sync auto-runs**: `rescrape_creators()` calls `auto_sync_reshaped()` by default — use `--no-sync` to skip
- **`run_sheets.py` argument pass-through**: Uses `parse_known_args()` to forward sub-command args — do NOT use `parse_args()` directly
- **`FollowerCount` shows "changed" even when same**: `_enrich_follower_count` always appends change entry when value is non-empty — cosmetic in change report, does not affect data
- **`run_sheets.py` import fix**: Must use `from scraper.run import rescrape_creators` (NOT `from code.scraper.run`) since `code/` is not a package
- **No credentials needed**: This repo never stores `credentials.json` or `token.json`. Google Sheets uses the Hermes subprocess adapter
- **`code/` cannot be a Python package**: The stdlib `code` module conflicts — `code/__init__.py` must NOT exist; sys.path manipulation handles imports instead
- **`sheets-export` skill is outdated**: The `sheets-export` skill still describes the OLD OAuth-based architecture. See README.md and code/sheets/client.py for the current subprocess adapter approach

See `references/scraper-pipeline-map.md` for the complete field mapping and data flow

## Testing

- `tests/test_scraper_merge.py` — 68 tests covering merge_scraped_row(), SafeEnricher, re-scrape enrichment, field preservation
- `tests/test_sheets.py` — 65 tests covering subprocess adapter, config validation, incremental append, clean_cell_value, EvidenceJSON, Unicode, backup
- Run: `python3 -m pytest tests/ -v` (133 total: 65 sheets + 68 merge)

- `cronjob` skill for scheduled scraping
- `web` skill for page extraction
- `sheets-export` skill for Google Sheets export workflow
