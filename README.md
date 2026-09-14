# Creator Research System

A safety-first agent workflow for building and maintaining a research
dataset (publicly available information about AI content creators)
through repeated discovery and scraping runs, without ever silently
losing or fabricating data.

## Project Structure

```text
Creator Research System/
├── AGENTS.md                              ← Agent workflow rules (17 sections)
├── SOUL.md                                ← Agent identity and purpose
├── README.md                              ← This file
├── code/
│   └── scraper/
│       ├── run.py                         ← Unified scraper dispatcher
│       ├── common.py                      ← Shared utilities (merge_to_crm, normalization)
│       ├── tiktok.py                      ← TikTok scraper
│       ├── facebook.py                    ← Facebook scraper
│       ├── instagram.py                   ← Instagram scraper
│       ├── linkedin.py                    ← LinkedIn scraper
│       ├── reddit.py                      ← Reddit scraper
│       ├── threads.py                     ← Threads scraper
│       ├── main.py                        ← YouTube scraper
│       ├── vimeo.py                       ← Vimeo scraper
│       ├── civitai.py                     ← Civitai scraper
│       ├── scrape_all.py                  ← All-platform batch scraper
│       └── model_client.py                ← AI classifier client
├── data/
│   ├── input/
│   │   └── input_channels.csv             ← Legacy (deprecated, not required by workflow)
│   ├── output/
│   │   ├── cron-discovery-log.md          ← Cron job execution log
│   │   ├── crm-cleanup-report.md          ← CRM cleanup validation report
│   │   └── *_scraped_output.csv           ← Per-platform scraper outputs
│   ├── Creator-Intel-CRM-List.csv         ← Master CRM (SINGLE SOURCE OF TRUTH)
│   └── backups/                           ← Timestamped CRM backups
├── obsidian/                              ← Knowledge base (in .gitignore)
│   ├── Creator Research/
│   │   ├── Creators/                      ← Individual creator notes
│   │   ├── Platforms/                     ← Platform documentation
│   │   ├── Daily/                         ← Daily research logs
│   │   ├── Projects/                      ← Project-specific notes
│   │   └── Research/                      ← Research findings
│   └── Attachments/
└── .gitignore                             ← Ignores obsidian/, .venv/, output CSVs
```

## Hermes Plugin

This project includes a native Hermes Plugin that exposes the scraper system as callable tools.

### Available Tools

| Tool | Description |
|------|-------------|
| `creator_scrape` | Scrape one public creator profile URL. Returns structured data. |
| `creator_batch_scrape` | Rescrape creators from Master CRM. Always creates backup first. |
| `creator_validate` | Validate Master CRM data quality. |

### Supported Platforms

| Platform | File | Method |
|----------|------|--------|
| TikTok | `code/scraper/tiktok.py` | Playwright |
| Instagram | `code/scraper/instagram.py` | Playwright |
| Facebook | `code/scraper/facebook.py` | Playwright |
| LinkedIn | `code/scraper/linkedin.py` | Playwright |
| Reddit | `code/scraper/reddit.py` | Playwright |
| Threads | `code/scraper/threads.py` | Playwright |
| YouTube | `code/scraper/main.py` | yt-dlp |
| Vimeo | `code/scraper/vimeo.py` | yt-dlp |
| Civitai | `code/scraper/civitai.py` | API |

### Architecture

```
Hermes Agent
    ↓
Plugin Tools (creator_scrape, creator_batch_scrape, creator_validate)
    ↓
plugin.yaml + __init__.py + schemas.py + tools.py
    ↓
Existing code/scraper/run.py dispatcher
    ↓
Existing platform scrapers (tiktok, instagram, facebook, etc.)
    ↓
Existing CRM merge (common.py) + backup
    ↓
data/Creator-Intel-CRM-List.csv (SINGLE SOURCE OF TRUTH)
```

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/apiz23/content-creator-system.git
cd content-creator-system

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Copy to Hermes plugins directory
cp -r . ~/.hermes/plugins/content-creator-system

# 4. Enable the plugin
hermes plugins enable content-creator-system

# 5. Verify it's loaded
hermes plugins list
```

### Using the Plugin

Once enabled, the tools appear automatically in your Hermes session:

```
# Scrape a single profile
hermes chat -q "Scrape https://www.tiktok.com/@example"

# Batch scrape Instagram
hermes chat -q "Scrape all Instagram profiles from the CRM"

# Validate data quality
hermes chat -q "Validate the CRM for duplicates and missing data"
```

### Example Prompts

#### Search & Discover Creators
```
"Find 5 AI video creators on TikTok"
"Search for AI artists on Instagram with more than 10K followers"
"Discover 10 YouTube channels about machine learning"
"Find AI content creators on TikTok and scrape their profiles"
```

#### Scrape Single Creator
```
"Scrape this TikTok profile: https://www.tiktok.com/@example"
"Extract data from https://www.instagram.com/ai_artist"
"Refresh this creator's information"
```

#### Batch Scrape from CRM
```
"Rescrape all existing TikTok creators"
"Refresh all Instagram profiles in the CRM"
"Batch scrape 10 creators from the CRM"
"Rescrape all creators (limit 5 per platform)"
```

#### Validate Data
```
"Check the CRM for duplicates"
"Validate data quality"
"Show me CRM statistics"
"Find missing URLs in the CRM"
```

#### Discovery Slash Command
```
/creator-discover platform:tiktok keywords:"AI video" count:5
/creator-discover platform:instagram keywords:"AI art" count:10
/creator-discover platform:youtube keywords:"machine learning" count:20
```

### Dependencies

The plugin requires these Python packages (same as the main project):

- pandas >= 2.0
- requests >= 2.28
- playwright >= 1.40
- python-dotenv >= 1.0
- yt-dlp >= 2024.1

Install them with:

```bash
pip install pandas requests playwright python-dotenv yt-dlp
```

### Configuration

No additional configuration is required. The plugin resolves paths relative to its own location, so it works regardless of your current working directory.

1. **Discovers** new content creators across platforms (TikTok, Facebook, Instagram, YouTube, LinkedIn, Reddit, Threads, Vimeo, Civitai)
2. **Scrapes** verified profiles using platform-specific Playwright-based scrapers
3. **Validates** every record through a mandatory Data Quality Gate before persistence
4. **Merges** into a master CRM using `merge_to_crm()` with safe-write procedure (read → check duplicate → update/append → validate → verify)
5. **Synchronizes** to an Obsidian knowledge base with wikilinked notes
6. **Automates** via scheduled cron jobs with continuity mode

## Core Principles

1. **Discovery and scraping are separate operations.** Discovery finds new subjects and queues them; scraping extracts data for queued subjects.
2. **Master data is append-only by default.** Every write follows: preserve existing data → deduplicate → append new data → verify.
3. **Nothing is fabricated.** Unverifiable fields are marked `Unknown`, never filled with a plausible guess.
4. **Completion requires verification.** A run isn't complete until the write has been re-read from disk and counts checked.
5. **Failures are reported, not hidden.** Records that couldn't be processed are preserved and marked as failed.
6. **Data Quality is mandatory.** Every record must pass validation (schema, normalization, deduplication, EvidenceJSON, CSV encoding, column count) before `merge_to_crm()` is called. See AGENTS.md Sections 17-18.

## Key Files

- **`AGENTS.md`** — Full agent workflow rules (17 sections covering data safety, normalization, scraping, Obsidian sync, cron jobs, and CRM Data Quality Gate)
- **`code/scraper/run.py`** — Unified dispatcher: `python3 code/scraper/run.py --url <profile-url> --limit 1`
- **`code/scraper/common.py`** — Shared utilities including `merge_to_crm()`, `load_and_clean_csv()`, `detect_platform_from_url()`, `extract_email()`
- **`data/Creator-Intel-CRM-List.csv`** — Master CRM (1053 rows as of Sep 14 2026)
- **`data/input/input_channels.csv`** — Persistent scraping queue (1001 rows)

## Scraper Usage

```bash
# Single profile
python3 code/scraper/run.py --url https://www.tiktok.com/@example --limit 1

# Platform batch
python3 code/scraper/run.py --platform tiktok --limit 5

# All platforms (batch mode)
python3 code/scraper/run.py --input data/input/input_channels.csv --limit 10
```

## Cron Jobs

Scheduled jobs use the `hermes cron` CLI with `--repeat` to auto-terminate:
```bash
hermes cron create "every 3m" "..." --name "Creator Research Discovery & Scrape Cycle" --repeat 5 --deliver origin --workdir "/path/to/project" --skill creator-research-system
```

## Data Safety Rules

- `data/input/input_channels.csv` is NEVER modified directly by scrapers
- `data/Creator-Intel-CRM-List.csv` is NEVER deleted or replaced
- `merge_to_crm()` uses case-insensitive ProfileURL matching to prevent duplicates
- Platform names are normalized to canonical casing (TikTok, Facebook, etc.)
- EvidenceJSON must be valid RFC 8259 JSON — never Python string representations
- CSV encoding is always UTF-8 without BOM, using `csv.QUOTE_MINIMAL`

## Status

Active internal project. The scraper code, CRM data, and knowledge-base contents are project-private.
