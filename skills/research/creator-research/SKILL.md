---
name: creator-research
description: Use for creator discovery, scraping, and CRM management.
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [Creator Research, Scraping, AI Content, Social Media]
    related_skills: [cronjob]
---

# Creator Research System

A safety-first workflow for building and maintaining a research dataset of publicly available creator information.

## Architecture

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

## Master CRM

**File:** `data/Creator-Intel-CRM-List.csv`

- Every creator appears exactly once (deduped by ProfileURL, case-insensitive)
- Updated (never replaced) when new scrape data arrives
- 19 columns: ProfileURL, Name/Handle, Platform, FollowerCount, Email, Tags, OutreachStatus, LastScrapedAt, Region, Language, PrimaryAITool, SampleContentURL, AIGCVerdict, DiscoveredAt, Source, Notes, FeedURL, ContactSourceURL, EvidenceJSON

**Legacy file:** `data/input/input_channels.csv` is deprecated — do NOT use in active workflow.

## Backup Rules

Every operation that modifies the Master CRM creates a backup first:
- Location: `data/backups/Creator-Intel-CRM-List_YYYYMMDD_HHMMSS.csv`
- If backup creation fails, the operation aborts
- Backups are never overwritten (unique timestamps)
- Previous backups are preserved

## Before Every Scrape

1. Record current CRM row count: `wc -l data/Creator-Intel-CRM-List.csv`
2. Create backup: `python3 -c "from common import backup_crm; backup_crm()"`
3. Verify backup exists before proceeding

## Running Scrapers

### Single Profile (Recommended)
```bash
source .venv/bin/activate
python3 code/scraper/run.py --url "https://www.tiktok.com/@example" --limit 1
```

### Batch Scrape
```bash
source .venv/bin/activate
python3 code/scraper/run.py --input data/input/civitai_input.csv
```

### Platform-Specific
```bash
source .venv/bin/activate
python3 code/scraper/civitai.py --limit 5
python3 code/scraper/reddit.py --limit 5
```

### Important: Do NOT call platform scrapers directly for CRM merges
- Platform scrapers write to `data/output/<platform>_scraped_output.csv` — they do NOT merge to CRM
- Only `run.py --url` and `run.py --input` handle CRM merge
- `--platform` mode does NOT merge to CRM

## After Scraping

1. Verify CRM row count matches or increased — NEVER decreased
2. Check output CSV for errors
3. Update README.md row count

## Discovery Workflow

### Natural Language (Recommended)

1. User: "Find 10 AI TikTok creators"
2. Hermes calls `web_search` with appropriate query
3. Hermes extracts candidate profile URLs from results
4. Hermes deduplicates against Master CRM (by ProfileURL)
5. Hermes calls `creator_scrape` for each new URL
6. Hermes calls `creator_validate` to confirm data quality

### Slash Command
```
/creator-discover platform:tiktok keywords:"AI video" count:10
/creator-discover platform:instagram keywords:"AI art" count:5
/creator-discover platform:youtube keywords:"machine learning" count:20
```

## Plugin Tools

| Tool | Description |
|------|-------------|
| `creator_scrape` | Scrape one public creator profile URL. Returns structured data. |
| `creator_batch_scrape` | Rescrape creators from Master CRM. Supports platform filter and limit. Always creates backup. |
| `creator_validate` | Validate Master CRM data quality (duplicates, schema, integrity). |

## CRM Merge Rules

- `merge_to_crm()` takes a single dict — updates existing or appends new
- `merge_results_to_crm()` takes a DataFrame — batch merge
- ProfileURL matching is case-insensitive + trailing-slash normalized
- Never bypass these functions with manual CSV writes

## Data Safety Rules

1. **Master CRM = single source of truth**
2. **Backup before every write** — abort if backup fails
3. **Never fabricate** — use empty string when data unavailable
4. **Always deduplicate** — check ProfileURL before adding (case-insensitive)
5. **Preserve existing valid data** — don't overwrite with empty/null/failed results
6. **Report partial success** — "7/10 scraped successfully"

## Example Prompts

```
"Find 5 AI creators on Instagram"
→ web_search → creator_scrape (×5) → creator_validate

"Scrape this TikTok profile: https://www.tiktok.com/@example"
→ creator_scrape

"Rescrape all existing creators"
→ creator_batch_scrape

"Refresh 10 TikTok profiles"
→ creator_batch_scrape (platform=tiktok, limit=10)

"Validate the CRM for duplicates"
→ creator_validate
```

## Output Formatting (Every Scrape)

1. **Follower normalization** — K/M/B notation (e.g. 4812 → 4.8K)
2. **Bio cleanup** — strip platform UI chrome (Malay, cookie banners)
3. **Locale** — en-US browser context for all Playwright scrapers
4. **Link resolution** — decode redirect URLs to canonical profile URLs
5. **EvidenceJSON** — must be valid RFC 8259 JSON

## Google Sheets Sync (Optional)

After successful CRM merge, `sync_crm_to_sheet()` pushes to Google Sheets if `GOOGLE_SHEETS_ENABLED=true`.

- Tab name: `Temp` (never change without explicit instruction)
- Auth: OAuth2 or Service Account
- Fails gracefully if credentials missing
- Rate limit (429) → wait 60s and retry

## Pitfalls

- **Civitai followers**: API doesn't expose followers; fetch web page for `followerCountAllTime`
- **Reddit blocks scraping**: Requires OAuth2; mark as `needs_manual_check`
- **Facebook Malay UI**: Set browser to English before scraping
- **Newlines in Notes**: Replace `\n` with spaces before CSV write
- **Duplicate ProfileURLs**: Always dedupe case-insensitively
- **Merge misalignment**: Ensure scraped CSV has `Name/Handle` (not `Handle`) and `ProfileURL` columns

## Backup Files

- Location: `data/backups/Creator-Intel-CRM-List_YYYYMMDD_HHMMSS.csv`
- Timestamped, never overwritten
- Previous backups preserved
- Verify backup exists after creation

## Related

- `cronjob` skill for scheduled scraping
- `web` skill for page extraction
