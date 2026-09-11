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
├── Code/
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
│   │   └── input_channels.csv             ← Persistent scraping queue
│   ├── output/
│   │   ├── cron-discovery-log.md          ← Cron job execution log
│   │   ├── crm-cleanup-report.md          ← CRM cleanup validation report
│   │   └── *_scraped_output.csv           ← Per-platform scraper outputs
│   ├── Creator-Intel-CRM-List.csv         ← Master CRM database
│   └── Creator-Intel-CRM-List.csv.backup  ← Pre-cleanup backup
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

## What This Project Does

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
- **`Code/scraper/run.py`** — Unified dispatcher: `python3 Code/scraper/run.py --url <profile-url> --limit 1`
- **`Code/scraper/common.py`** — Shared utilities including `merge_to_crm()`, `load_and_clean_csv()`, `detect_platform_from_url()`, `extract_email()`
- **`data/Creator-Intel-CRM-List.csv`** — Master CRM (1049 rows as of Sep 11 2026)
- **`data/input/input_channels.csv`** — Persistent scraping queue (1001 rows)

## Scraper Usage

```bash
# Single profile
python3 Code/scraper/run.py --url https://www.tiktok.com/@example --limit 1

# Platform batch
python3 Code/scraper/run.py --platform tiktok --limit 5

# All platforms (batch mode)
python3 Code/scraper/run.py --input data/input/input_channels.csv --limit 10
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
