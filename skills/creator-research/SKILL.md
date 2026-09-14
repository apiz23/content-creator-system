---
name: creator-research-system
description: Safe, verifiable workflow for discovering, scraping, classifying, and organizing publicly available information about content creators. Use this whenever the user asks to discover/find new creators, scrape a platform, refresh creator data, or run creator research workflows. Master CRM is the single source of truth.
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

This is the authoritative dataset for ALL creators. All operations read from and write to this file.

**Legacy file:** `data/input/input_channels.csv` is deprecated and not required by the active workflow.

## Backup Rules

Every operation that modifies the Master CRM creates a backup first:
- Location: `data/backups/Creator-Intel-CRM-List_YYYYMMDD_HHMMSS.csv`
- If backup creation fails, the operation aborts
- Backups are never overwritten (unique timestamps)
- Previous backups are preserved

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
