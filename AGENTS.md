```
# AGENTS.md

## Project: Creator Research

### Purpose

This project is used to discover, research, analyze, validate, and organize publicly available information about content creators.

The primary focus is creators related to:

- Artificial Intelligence
- Generative AI
- AI Video
- AI Image Generation
- AI Tools
- Software Development
- Technology
- Developer Tools
- Content Creation

The project uses Hermes as the AI agent, DeepSeek as the primary reasoning/coding model, and Python for scraping and data processing.

---

# 1. CRITICAL RULES

These rules override all other instructions. Never violate them.

## 1.1 Never Destroy Master Data

The following files are MASTER DATA and must NEVER be deleted, replaced, overwritten destructively, truncated, or recreated from only the latest search/discovery results:

1. `data/Creator-Intel-CRM-List.csv`
2. `data/input/input_channels.csv`

Default behavior is ALWAYS:

```
PRESERVE EXISTING DATA → DEDUPLICATE → APPEND NEW DATA → VERIFY
```

## 1.2 Never Fabricate

Never guess or invent:

- Creator names, usernames, handles
- Follower counts, email addresses
- Locations, languages, AI tools
- Profile URLs, sample content URLs
- Engagement metrics

Use `Unknown` when information cannot be verified.

## 1.3 Never Claim Completion Without Verification

Never say "complete" until ALL required steps have been verified. If a step fails, report the failure instead of claiming success.

## 1.4 Discovery ≠ Scraping

- **Discovery** finds new creators and adds them to the input queue. It does NOT run scrapers.
- **Scraping** reads the input queue, runs scrapers, and saves output. It does NOT perform web discovery.

Only combine them when the user explicitly asks for both.

---

# 2. AUTHORITATIVE FILES

| File | Purpose | Can Replace? |
|------|---------|--------------|
| `data/input/input_channels.csv` | Persistent scraping queue | ❌ Never |
| `data/Creator-Intel-CRM-List.csv` | Master CRM database | ❌ Never |
| `data/output/*_scraped_output.csv` | Latest scraper output | ✅ Can refresh |
| `data/output/creator_discovery.csv` | Optional discovery report | ✅ Can refresh |

## 2.1 input_channels.csv

Purpose: Persistent scraping queue.

Rules:
- APPEND new verified creators
- DO NOT replace with only new discoveries
- DO NOT remove existing records
- Preserve existing columns and their order
- Deduplicate before appending

## 2.2 Creator-Intel-CRM-List.csv

Purpose: Master CRM database.

Rules:
- APPEND new records
- UPDATE existing records only when new verified information is available
- DO NOT replace with platform output
- DO NOT delete existing creators unless user explicitly requests
- Preserve existing schema and column order

## 2.3 Platform Output CSVs

Purpose: Latest scraper result. Intermediate outputs, NOT master database.

After scraping, merge/update into the Master CRM.

## 2.4 creator_discovery.csv

Purpose: Optional reporting artifact only. NOT authoritative.

Must NEVER replace:
- `data/input/input_channels.csv`
- `data/Creator-Intel-CRM-List.csv`

---

# 3. DISCOVERY WORKFLOW

When the user asks to discover/find/search for new creators:

```
SEARCH
    ↓
VERIFY CREATOR
    ↓
VERIFY PROFILE URL
    ↓
CHECK FOR DUPLICATE (input CSV + Master CRM)
    ↓
APPEND TO data/input/input_channels.csv
    ↓
APPEND/UPDATE data/Creator-Intel-CRM-List.csv
    ↓
UPDATE PLATFORM NOTE
    ↓
UPDATE DAILY LOG
    ↓
CHECK PROJECT/RESEARCH IF RELEVANT
    ↓
VERIFY EVERYTHING
    ↓
REPORT COMPLETE
```

## 3.1 Discovery Triggers

Perform discovery ONLY when the user explicitly asks to:

- discover a creator
- find creators / find new creators
- search for creators
- find TikTok creators / find AI creators
- discover new profiles
- add creators to the input CSV

Do NOT automatically discover during a normal scrape.

## 3.1.1 Search vs Discovery

- "search for creators" or "search for new creators" → triggers discovery (web search for new creators)
- "search" alone (without "for creators") → search EXISTING records in input CSV / CRM for a specific creator. Does NOT trigger discovery.
- If the user says just "search" without specifying existing vs new, default to DISCOVERING new creators (treat as "search for new creators").
- "scrape" → runs the scraper on existing input queue. Does NOT trigger discovery.

## 3.2 Discovery Source

Discovery may use:

- Web search
- Public platform search
- Public creator directories
- Other publicly available sources

## 3.3 New Creator Count

When the user requests N NEW creators (e.g., "Find 5 new TikTok creators"):

- N means N genuinely new, verified, deduplicated creators
- Existing creators and duplicates do NOT count toward N
- Continue discovery until N qualifying new creators are found
- Report: candidates reviewed, duplicates skipped, rejected candidates, genuinely new creators added

## 3.4 Duplicate Protection

Before adding a discovered creator:

1. Compare ProfileURL
2. Compare normalized handle
3. Search the Creators folder
4. Check the input CSV
5. Check the Master Creator CRM

If the creator already exists:

- Do not add another CSV row
- Do not add another CRM row
- Update existing CRM information if appropriate
- Report that the creator already existed

## 3.5 Discovery → Input CSV

When a creator is discovered and verified:

1. Read the existing CSV
2. Check whether the creator/profile URL already exists
3. Preserve the existing CSV schema
4. Append the new creator as a new row
5. Verify that the CSV remains valid
6. Do not automatically scrape the creator

## 3.6 Discovery → Master CRM

When a creator is discovered and verified:

1. Read the existing Master CRM
2. Identify the creator using the strongest available identifier:
   - ProfileURL
   - Platform + normalized handle
   - Creator name where appropriate
3. Check for duplicates
4. If the creator already exists → UPDATE the existing row
5. If the creator does not exist → APPEND a new row
6. Preserve existing useful information
7. Never fabricate missing values

## 3.7 Discovery Completion

Do not say discovery is complete until:

- [ ] Creator discovered
- [ ] Profile URL verified
- [ ] Duplicate check completed
- [ ] Input CSV updated
- [ ] Master Creator CRM updated
- [ ] Platform note updated
- [ ] Daily log updated
- [ ] Relevant Project checked
- [ ] Relevant Research checked
- [ ] Changes verified

## 3.8 Discovery Example

User: "Find 1 TikTok creator who makes AI content."

Expected workflow:

```
Web Search
    ↓
Find suitable creator
    ↓
Verify TikTok URL
    ↓
Check input CSV
    ↓
Check Master CRM
    ↓
Append to input_channels.csv
    ↓
Append to Creator-Intel-CRM-List.csv
    ↓
Update TikTok platform note
    ↓
Update today's Daily note
    ↓
Check Projects/Research
    ↓
Verify
    ↓
Report
```

Expected response:

```
Discovery complete.

- Creator: @example
- Platform: TikTok
- Profile: verified
- Added to: data/input/input_channels.csv
- Added to: data/Creator-Intel-CRM-List.csv
- Platform note: Platforms/TikTok.md updated
- Daily log: Daily/2026-09-01.md updated
- Scraping: NOT performed
```

---

# 4. SCRAPING WORKFLOW

When the user asks to "scrape", "scrape [platform]", "run the scraper", or "refresh creator data":

```
READ INPUT CSV
    ↓
FILTER REQUESTED PLATFORM
    ↓
RUN SCRAPER
    ↓
SAVE CSV TO data/output/
    ↓
VERIFY CSV
    ↓
UPDATE MASTER CRM
    ↓
SYNC PLATFORM NOTE
    ↓
SYNC DAILY LOG
    ↓
CHECK PROJECT/RESEARCH
    ↓
VERIFY EVERYTHING
    ↓
REPORT COMPLETE
```

## 4.1 Scrape Triggers

Scrape ONLY when the user explicitly asks to:

- scrape
- run the scraper
- scrape TikTok / scrape Facebook / scrape Threads
- scrape all platforms
- refresh creator data

Do NOT perform web discovery during a scrape.

## 4.2 Scrape Input

The input CSV is the source of truth for scraping.

1. Read `data/input/input_channels.csv`
2. Filter by the requested platform
3. Never invent creator URLs for scrape operations
4. Never use web search for scraper input

## 4.3 Platform Routing

Each scraper is a standalone Python script run with `python3 <file>` from the repo root (or the `.venv` activated). All 10 scripts read from `data/input/input_channels.csv`, filter by platform, and write to their platform-specific output CSV. There are no CLI arguments, flags, or subcommands — every scraper processes the entire filtered input file at once.

**`code/scraper/run.py`** is the unified dispatcher. It supports three modes: `--platform`, `--url`, and `--input` (full-CSV batch). After dispatching each profile, `run.py` automatically merges results into `data/Creator-Intel-CRM-List.csv` using the safe-write procedure (read → check duplicate by ProfileURL → update or append → validate → write → re-read to verify). `run.py` also writes intermediate results to `data/output/run_dispatch_output.csv` (URL mode) or `data/output/batch_dispatch_output.csv` (batch mode).

| Platform | Script | Input | Output | Preconditions | Delay |
|---|---|---|---|---|---|
| **Civitai** | `code/scraper/civitai.py` | `data/input/input_channels.csv` | `data/output/civitai_scraped_output.csv` | No browser needed. Public API. Requires `requests`, `pandas`. | 1s |
| **Facebook** | `code/scraper/facebook.py` | `data/input/input_channels.csv` | `data/output/facebook_scraped_output.csv` | Playwright + Chromium installed. Requires `playwright`, `requests`, `pandas`. | 2s |
| **Instagram** | `code/scraper/instagram.py` | `data/input/input_channels.csv` | `data/output/instagram_scraped_output.csv` | Playwright + Chromium installed. Requires `playwright`, `requests`, `pandas`. | 3s |
| **LinkedIn** | `code/scraper/linkedin.py` | `data/input/input_channels.csv` | `data/output/linkedin_scraped_output.csv` | Playwright + Chromium installed. Requires `playwright`, `requests`, `pandas`. | 2.5s |
| **Reddit** | `code/scraper/reddit.py` | `data/input/input_channels.csv` | `data/output/reddit_scraped_output.csv` | Playwright + Chromium installed. Requires `playwright`, `requests`, `pandas`. | 1.5s |
| **Threads** | `code/scraper/threads.py` | `data/input/input_channels.csv` | `data/output/threads_scraped_output.csv` | Playwright + Chromium installed. Requires `playwright`, `requests`, `pandas`. | 1.5s |
| **TikTok** | `code/scraper/tiktok.py` | `data/input/input_channels.csv` | `data/output/tiktok_scraped_output.csv` | Playwright + Chromium installed. Requires `playwright`, `requests`, `pandas`. | 2s |
| **YouTube** | `code/scraper/main.py` | `data/input/input_channels.csv` | `data/output/youtube_refreshed_output.csv` | `yt-dlp` installed (`.venv/bin/yt-dlp`). No browser needed. Requires `yt-dlp`, `requests`, `pandas`. | None (yt-dlp self-manages) |
| **Vimeo** | `code/scraper/vimeo.py` | `data/input/input_channels.csv` | `data/output/vimeo_scraped_output.csv` | `yt-dlp` installed (`.venv/bin/yt-dlp`). No browser needed. Requires `yt-dlp`, `requests`, `pandas`. | 1s |
| **All-in-one** | `code/scraper/scrape_all.py` | `data/input/input_channels.csv` | `data/output/all_scraped_output.csv` | Playwright + Chromium + `yt-dlp` installed. Supports all platforms in one pass. | Varies by platform order |
|---|---|---|---|---|---|
| **Flag** | **All platforms** | — | — | `python3 code/scraper/<platform>.py --limit N` processes only the first `N` matching rows for that platform after platform filtering, in memory; omitting it processes all matching rows and preserves current behavior. `input_channels.csv` is never modified by a scraper run. |

### Invocation command

```bash
python3 code/scraper/<platform>.py
```

Example:
```bash
python3 code/scraper/tiktok.py
```

There are no CLI arguments. Every scraper reads the entire `data/input/input_channels.csv`, filters rows matching its platform, processes all matching rows, and writes the output CSV. To limit which creators get scraped, filter the input CSV before running the scraper.

### Environment variables

All scrapers that use the AI classifier read from `code/scraper/model_client.py`, which loads `.env` from the project root. Required variables:
- `MODEL_PROVIDER` (default `ollama`)
- `MODEL_NAME` (default `qwen3.5:latest`)
- `OLLAMA_BASE_URL` (default `http://localhost:11434`)
- For `MODEL_PROVIDER=api`: `API_BASE_URL`, `API_KEY`

### Preconditions checklist

Before running any scraper:
1. **Python venv active**: `.venv/bin/python` or `source .venv/bin/activate`. The project uses `.venv`.
2. **Dependencies installed**: `pip install -r requirements.txt` — this includes `python-dotenv`, `playwright`, `pandas`, `requests`, `yt-dlp`.
3. **Playwright browsers installed** (for browser scrapers): `playwright install chromium`. This is required for Facebook, Instagram, LinkedIn, Reddit, Threads, TikTok.
4. **yt-dlp available** (for YouTube and Vimeo): `yt-dlp` must exist at `.venv/bin/yt-dlp` or on `PATH`.
5. **Ollama running** (if using default provider): `ollama serve` must be running at `http://localhost:11434`. The AI classifier calls this on every profile. If Ollama is offline, the scraper falls back to rule-based classification.
6. **Input CSV exists**: `data/input/input_channels.csv` must be present and populated. If empty, the scraper reports zero profiles found.
7. **Working directory**: The repo root (`.venv` sibling directory). Scripts use `Path(__file__).resolve().parent.parent` to find data files, so they work from any cwd as long as the `.venv` is active and `model_client.py` is importable.

### Typical runtime and failure modes

- **Runtime**: Each profile takes roughly 2–5 seconds for browser-based platforms (page load + AI classification). A full input file of 900+ creators could take hours. YouTube/Vimeo with `yt-dlp` are faster per profile but slower overall for large channels.
- **Known failure modes**:
  - **Playwright browser launch failure**: Usually means Chromium is not installed (`playwright install chromium`).
  - **Ollama offline**: The AI classifier catches the exception and falls back to rule-based classification. The scraper continues but with less accurate tags. Check `call_model()` errors in the output.
  - **Rate limiting / bot walls**: Some platforms (Facebook, LinkedIn, Instagram) aggressively throttle. Signs include HTTP 403/429, empty DOM extracts, or `PageError` exceptions. These are caught per-record and logged as `[-] Error scraping ...`.
  - **Empty output CSV**: Usually means the input CSV has no rows matching the platform filter. Check `data/input/input_channels.csv` for rows with the correct `Platform` column value.
  - **`ModuleNotFoundError: No module named 'dotenv'`**: The wrong Python interpreter is running. Use `.venv/bin/python` or activate `.venv`.
  - **YouTube/Vimeo `ModuleNotFoundError: No module named 'yt_dlp'`**: `yt-dlp` not installed in the venv. Run `pip install yt-dlp` or check `.venv/bin/yt-dlp`.
  - **`response.json()` or JSON parse errors**: The model returned an unexpected format. Caught by the exception handler; fallback classification applies.
  - **`AttributeError: 'NoneType' object has no attribute 'replace'`** (Vimeo): A pre-existing type issue where `uploader_name` is `None`. Does not crash the run but may log an error for specific profiles.

### Post-scrape workflow

After scraping completes:
1. **Verify output CSV**: Check `data/output/<platform>_scraped_output.csv` exists and has the expected row count.
2. **Sync to CRM**: Run `code/scraper/sync_tiktok_crm.py` (or the equivalent sync script for the platform) to merge output into `data/Creator-Intel-CRM-List.csv`.
3. **Report counts**: Successful records, failed records, new vs. updated in CRM.

Note: `scrape_all.py` is the all-in-one runner that handles all platforms sequentially. It supports Civitai, YouTube, Vimeo, Threads, TikTok, Instagram, Facebook, LinkedIn, and Reddit in a single pass. Use it for "scrape all platforms" requests.

## 4.4 Scrape Output

Save scraped results to `data/output/` using platform-specific filenames:

- `threads_scraped_output.csv`
- `tiktok_scraped_output.csv`
- `instagram_scraped_output.csv`
- `facebook_scraped_output.csv`
- `linkedin_scraped_output.csv`
- `reddit_scraped_output.csv`
- `youtube_refreshed_output.csv`
- `vimeo_scraped_output.csv`
- `civitai_scraped_output.csv`

Platform outputs are intermediate, not the master database. Merge/update into Master CRM after scraping.

## 4.5 Scrape → CRM Update

After scraping a creator, ALWAYS update the corresponding record in:

`data/Creator-Intel-CRM-List.csv`

For every creator in the output:

1. Check if creator exists in Master CRM
2. If exists → UPDATE the existing row with new verified information
3. If not exists → APPEND a new row
4. Never replace the entire CRM with scraper output
5. Never blank existing fields because scraper returned empty
6. Never replace verified data with Unknown

## 4.6 Scrape Completion

The word "complete" MUST NOT be used until:

- [ ] Scraper finished
- [ ] CSV saved to `data/output/`
- [ ] CSV verified
- [ ] Master Creator CRM updated
- [ ] Platform note synchronized
- [ ] Daily log synchronized
- [ ] Relevant Project notes checked
- [ ] Relevant Research notes checked

If any step fails, report exactly what failed and continue fixing it where possible.

## 4.7 Scrape Report

After every scraper execution, report:

- Platform scraped
- Scraper executed
- Input file
- Output file
- Records found in input
- Records successfully scraped
- Records failed
- Daily log created/updated
- Overall status: `SUCCESS`, `PARTIALLY COMPLETED`, or `FAILED`

## 4.8 Simple Scrape Command

User: `scrape Facebook`

Hermes MUST:

1. Read `data/input/input_channels.csv`
2. Find Facebook profiles
3. Run Facebook scraper
4. Save `data/output/facebook_scraped_output.csv`
5. Verify results
6. Update Master Creator CRM
7. Update `Platforms/Facebook.md`
8. Update `Daily/YYYY-MM-DD.md`
9. Check relevant Projects/Research
10. Verify synchronization
11. Report completion

## 4.9 Existing Output Files

If the requested scraper discovers that an output CSV already exists:

- DO NOT automatically assume it represents the current run
- Check: file modification time, scraper execution result, number of records
- If the current scrape was not actually executed, clearly state that
- If the user explicitly asks to refresh/re-scrape, run the scraper

## 4.10 Data Priority

When information exists in multiple places, prefer the newest verified information:

```
CURRENT VERIFIED SCRAPE
    ↓
PREVIOUS VERIFIED SCRAPE
    ↓
DISCOVERY DATA
    ↓
OLD EXISTING DATA
```

Never overwrite reliable existing information with empty or failed scrape results. If a new scrape fails to retrieve follower count, DO NOT replace an existing verified follower count with "N/A".

---

# 5. MASTER CSV SAFETY

## 5.1 Safe Write Procedure

Before modifying a master CSV:

1. Check that the file exists
2. Read the current contents
3. Record the current row count
4. Create an in-memory copy of the existing dataset
5. Apply the intended append/update operation
6. Validate the resulting dataset
7. Write the updated dataset safely
8. Re-read the saved file
9. Verify:
   - Previous row count
   - Existing record identifiers still present
   - New records added
   - Column names unchanged
   - Column order unchanged
   - No unexpected rows deleted
10. Report: Previous row count, new creators discovered, duplicates skipped, records added, final row count

If validation fails, DO NOT overwrite the original file. Preserve the original and report the failure.

## 5.2 Append, Don't Replace

FORBIDDEN behavior:

```text
Existing CSV: 100 creators
New search: 5 creators

WRONG: Replace CSV → 5 creators

CORRECT: 100 existing + 5 genuinely new → 105 creators

If 2 of the 5 are already present:
100 existing + 3 genuinely new → 103 creators
```

## 5.3 Safety Check

If there is ANY uncertainty about whether an operation will replace or destroy existing data:

STOP before writing and ask the user for confirmation.

Do NOT assume that "update", "sync", "refresh", "save", "rebuild", or "regenerate" means replacing the dataset.

## 5.4 Deletion Policy

Never delete existing creator data unless the user explicitly says:

"Delete [specific records] from [specific file]."

Without explicit deletion instructions, existing creator records are considered protected.

---

# 6. DATA QUALITY

## 6.1 Information Categories

Clearly distinguish between:

- **Verified facts**: Directly confirmed from public source
- **Extracted information**: Pulled from profile/page content
- **AI-generated analysis**: Inference from available data (NOT factual evidence)
- **Reasonable inference**: Logical deduction from verified facts
- **Unknown**: Information that cannot be verified

## 6.2 Evidence

Important information should have evidence:

```json
{
  "followers": {
    "value": "528K",
    "source": "SOURCE_URL",
    "verified_at": "YYYY-MM-DD"
  }
}
```

Never claim information is verified when there is no supporting source.

## 6.3 AI Analysis

When using Hermes or DeepSeek for analysis:

- Do not treat AI output as automatically verified
- Separate facts from conclusions
- Do not invent evidence or create fake citations
- Base conclusions on available evidence

Example:

```
Verified: The creator publicly mentions using Runway.
Inference: The creator appears to specialize in AI video content.
```

## 6.4 Public Information

Only collect information that is publicly accessible:

- Name, username/handle, platform, profile URL
- Public follower count, biography, website
- Public business email
- Content niche, location, language
- Publicly mentioned AI tools
- Sample content URLs, source URLs
- Discovery date, last verified date

Do not access private information, private accounts, passwords, tokens, or unauthorized areas.

---

# 7. SCRAPER DEVELOPMENT

## 7.1 Principles

Before creating a new scraper:

1. Inspect existing scrapers
2. Understand the current architecture
3. Determine whether an existing scraper can be extended
4. Reuse existing utilities where possible
5. Create new code only when necessary

Typical scraper location: `code/scraper/`

## 7.2 Modifying Scrapers

1. Read the existing implementation
2. Understand the current behavior
3. Identify the actual problem
4. Make the smallest appropriate change
5. Run the scraper or relevant test
6. Inspect the output
7. Verify that the change works
8. Document important changes

Use: clear functions, meaningful variable names, error handling, logging, validation, reasonable retries, reasonable delays.

Avoid unnecessary rewrites.

## 7.3 Crawl4AI

Crawl4AI is installed in this project. Use it when it provides a reliable advantage for browser-based scraping, but do not automatically replace existing platform scrapers.

Test Crawl4AI against the existing scraper before replacing one.

## 7.4 AI Classification

AI classification must remain separate from the scraping layer. The scraper collects raw information first. The AI classification layer determines tags, PrimaryAITool, AIGCVerdict, Language, Evidence.

Do not hardcode the AI provider into scraping logic.

---

# 8. ERROR HANDLING

When something fails:

1. Read the complete error
2. Identify the actual cause
3. Inspect the relevant code or config
4. Determine whether the problem is temporary or permanent
5. Make the smallest appropriate fix
6. Test again
7. Verify the result
8. Report the problem if it remains unresolved

Do not hide errors. Do not silently ignore failed scraping attempts.

If a profile cannot be scraped:

1. Do not silently pretend it succeeded
2. Preserve the original input record
3. Mark the result as failed where supported
4. Record the reason in Notes or an appropriate failure field
5. Continue processing the remaining profiles
6. Report successful and failed counts to the user

---

# 9. REPORTING

When reporting completed work, use a clear structure:

```
Completed:
- Found 25 candidate creators.
- Verified 18 creators.
- Removed 7 duplicates or irrelevant profiles.
- Added 18 records to the dataset.

Issues:
- 3 profiles could not be verified.
- 2 pages blocked automated access.

Next steps:
- Review the unverified profiles.
- Continue discovery if more creators are required.
```

Clearly distinguish: completed work, verified information, assumptions, errors, unresolved issues, recommended next steps.

---

# 10. PROJECT STRUCTURE

The actual project structure:

```text
Creator Research System/
├── AGENTS.md
├── SOUL.md
├── code/
│   └── scraper/
│       ├── civitai.py
│       ├── facebook.py
│       ├── instagram.py
│       ├── linkedin.py
│       ├── main.py
│       ├── reddit.py
│       ├── scrape_all.py
│       ├── threads.py
│       ├── tiktok.py
│       └── vimeo.py
├── analysis/
├── data/
│   ├── input/
│   │   └── input_channels.csv
│   ├── output/
│   │   ├── all_scraped_output.csv
│   │   ├── civitai_scraped_output.csv
│   │   ├── facebook_scraped_output.csv
│   │   ├── free_scraped_influencers.csv
│   │   ├── instagram_scraped_output.csv
│   │   ├── linkedin_scraped_output.csv
│   │   ├── threads_scraped_output.csv
│   │   ├── tiktok_scraped_output.csv
│   │   └── youtube_refreshed_output.csv
│   └── Creator-Intel-CRM-List.csv
└── .gitignore
```

IMPORTANT:

- The project uses lowercase `data/`, not `Data/`
- The input directory is `data/input/`
- The output directory is `data/output/`
- Scrapers are stored in `code/scraper/`

Do not invent alternative directories unless the user explicitly requests a restructuring.

---

# 11. VERSION CONTROL

If Git is used:

- Review changes before committing
- Check for API keys, passwords, tokens, cookies, session data, private credentials
- Never commit secrets
- Use `.gitignore` appropriately

---

# 12. SECRETS

Never place secrets inside:

- Source code, Markdown notes
- CSV files, JSON files, README files
- Git commits

Use environment variables or appropriate secret storage. Examples: `DEEPSEEK_API_KEY`, `API_KEY`, `PASSWORD`, `ACCESS_TOKEN`, `SESSION_TOKEN`, `COOKIE`.

Never expose actual secret values.

---

# 13. DATA PROCESSING

Use deterministic code whenever possible.

Prefer Python for: scraping, parsing, cleaning, normalization, deduplication, validation, CSV/JSON processing.

Use AI for: classification, summarization, relevance analysis, content analysis, reasoning, research assistance.

Do not use AI unnecessarily for operations that can be performed reliably with deterministic code.

---

# 14. DATA PIPELINE

The preferred workflow:

```
Web Search
    ↓
Creator Discovery
    ↓
Public Profile
    ↓
Scraping
    ↓
Raw Data
    ↓
Cleaning
    ↓
Normalization
    ↓
Validation
    ↓
AI Analysis
    ↓
Final Dataset
```

Keep raw data separate from processed data. Do not overwrite raw data unnecessarily.

---

# 15. FILE MANAGEMENT

Before editing a file:

1. Read the relevant file
2. Understand its purpose
3. Preserve existing useful content
4. Make only the required changes
5. Verify the result

Do not delete or replace files without a clear reason. Do not create unnecessary duplicate files. Use descriptive filenames.

## Python File Creation & Hygiene

Before creating any new `.py` file, check whether existing functionality can be reused or extended. Do not create a new Python file merely because an existing file is large — only split functionality into a new file when it represents a genuinely separate responsibility or improves maintainability.

For temporary debugging, verification, testing, or one-off work, treat the file as scratch work and delete it immediately after the task that required it is complete. Scratch-file naming patterns: `test.py`, `test_*.py`, `debug.py`, `debug_*.py`, `check.py`, `check_*.py`, `verify.py`, `verify_*.py`, `temp.py`, `temp_*.py`, `*_test.py`, and other one-off scripts. Never leave these in the project root or production directories unless they are intentionally part of the project.

Before deleting any Python file, inspect its references/usages if there is any uncertainty about whether it is important. Never delete a potentially important Python file solely because its name looks temporary.

Do not create new Python files during cleanup unless absolutely necessary.

---

The overall objective is to produce creator intelligence that is:

**Accurate + Verifiable + Structured + Reusable + Well-organized.**

---

# 16. CRM DATA QUALITY & CSV FORMATTING

This section ensures every creator record persisted in `data/Creator-Intel-CRM-List.csv` is strictly verified, normalized, schema-compliant, deduplicated, and safe to persist. The system follows a **Validation-Before-Persistence** architecture:

```
Search → Discover → Verify → Deduplicate → Scrape → Data Quality Gate → merge_to_crm() → Post-Merge CSV Validation
```

**Do not rely on downstream cleanup scripts.** If a record fails validation and cannot be safely normalized, reject it.

## 16.1 CSV Data Contract & Schema Guardrails

Before preparing any record for CRM insertion, enforce the active schema:

- **Strict Column Order & Count:** Do not alter the existing column ordering, add arbitrary columns, rename headers, or drop fields. Every record must match the exact column count of the header row.
- **Empty Field Handling:** If a value is unavailable or unverified, use the CRM's standard null/empty representation (empty string `""`). Do not inject placeholders like `"N/A"`, `"None"`, `"null"`, or `"Unknown"`.
- **Prohibited Injections:** Normal creator fields must never contain:
  - Python dictionaries, tuples, or lists (e.g., `['tag1', 'tag2']`)
  - Raw unescaped JSON
  - Debugging logs, stack traces, or scraper error dumps
  - Model reasoning or chain-of-thought traces
  - Raw search engine SERP snippets
  - HTML, CSS, or navigation tags
  - Platform interface noise

## 16.2 Normalization Rules

### Platform Names
Enforce canonical casing:
- Civitai, Facebook, Instagram, LinkedIn, Reddit, Threads, TikTok, Vimeo, YouTube

Transform common variations (e.g., `tiktok`, `TIKTOK` → `TikTok`; `fb`, `facebook` → `Facebook`). Preserve verified niche platforms only when accompanied by explicit evidence.

### Handles
- Normalize handles uniformly across all lookups (e.g., strip redundant `@` prefixes, spaces, and trailing symbols during matching).
- Never store complete profile URLs, tracking queries, or internal database keys as the `Handle` unless the platform strictly uses that identifier.
- Store canonical profile URLs in the dedicated URL column, completely separated from the handle.

### Creator & Channel Names
- Extract the genuine human, brand, or channel display name.
- Explicitly reject platform navigation text, page titles representing errors (e.g., "Page Not Found", "Log In / Sign Up"), raw numeric user IDs (e.g., Facebook internal numeric IDs like `100088664633967`), and SERP titles.

## 16.3 Profile URL Sanitization

- Strip all tracking parameters (`utm_*`, `fbclid`, `si`, `ref`, etc.) and non-essential hash fragments.
- Store canonical profile/channel base URLs only.
- **Strict Rejection:** Never store search engine URLs (Google, Bing), platform search queries (e.g., `tiktok.com/search?q=...`), hashtag feeds, or generic directory aggregators as creator URLs.

## 16.4 Pre-Scrape & Pre-Merge Deduplication

Before spending compute to scrape or attempting to merge, perform case-insensitive duplicate checks across:
1. `data/input/input_channels.csv`
2. `data/Creator-Intel-CRM-List.csv`

Matching criteria:
- Same platform + matching handle (case-insensitive, e.g., `@CreatorName` == `@creatorname`)
- Matching canonical profile URL
- Confirmed alias or matching channel ID

If a match is found in either file, mark it as a duplicate and skip insertion.

## 16.5 Discovery & Search Result Validation

Search results are leads, not verified records:
1. Confirm the creator profile actually exists and belongs to a real entity matching the research criteria.
2. Extract bio, handles, and metadata directly from the source profile, not from search engine preview snippets.
3. Reject generic landing pages, topic/category hubs, community group sidebars, and spam directories.

## 16.6 The Scraped Data Quality Gate

After running the scraper (e.g., `python3 code/scraper/run.py --url <profile-url> --limit 1`), inspect the output before touching the CRM:

- **Facebook Artifact Detection:** Detect and eliminate common scraped UI/navigation artifacts (e.g., `Lagi`, `Rakan`, `Foto`, `Perihal`, `Pekerjaan`, `mengikuti`, `Siaran`, `tempat ker`, `Tiada`). Only strip these tokens when they represent platform UI noise—never truncate legitimate creator bios.
- **Content Integrity:** Verify fields contain substantive human text. If scraping fails or hits a login wall, reject the payload rather than persisting garbage or partial UI text.

## 16.7 EvidenceJSON Formatting

- Must parse as valid RFC 8259 JSON.
- Never output Python string representations (e.g., do not output `{'status': 'verified'}`). Use valid double-quoted JSON: `{"status": "verified"}`.
- Properly escape all internal quotes, backslashes, and line breaks so they do not fracture CSV columns.
- If evidence is malformed and cannot be reliably parsed or reconstructed, drop the invalid segment rather than saving corrupted text.

## 16.8 CSV Encoding & Delimiter Safety

- **Tooling Contract:** Never construct or append CSV rows using manual string formatting or raw string concatenation.
- **Escaping:** Use standard CSV libraries (`csv.writer` with `csv.QUOTE_MINIMAL` or `csv.QUOTE_ALL`) to safely encapsulate fields containing commas, line breaks, emojis, and quotes.
- **Character Encoding:** Always read and write using `utf-8` without BOM. Ensure international text, Malay terms, and Unicode characters remain uncorrupted.

## 16.9 Column Count & Header Integrity

- **Header Locking:** The CSV header line is immutable. Never duplicate, append, or re-insert header rows into the data body.
- **Row Width Invariant:** If the header defines $N$ columns, every single row written to the file must parse to exactly $N$ fields.
- **Immediate Abort:** If an output row produces $N \pm 1$ columns, abort the merge immediately, roll back the write, and flag the faulty record.

## 16.10 Merge Safety & Target Invariants

- **Controlled Ingestion:** Never bypass the designated `merge_to_crm()` utility. All writes must go through this centralized merge path.
- **Protected Files:** `data/input/input_channels.csv` is read-only for this process. Never modify, overwrite, or delete input records.
- **Update Behavior:** When merging new information for an existing creator, preserve established, verified records. Do not overwrite populated fields with empty values or lower-confidence data.

## 16.11 Failure Handling

If an entry fails any validation step:
1. **Drop / Skip:** Do not attempt to force, fabricate, or guess missing information.
2. **Log:** Note the specific failure mode (e.g., `[SKIP] Invalid handle format: <val>`, `[SKIP] Duplicate detected: <val>`, `[REJECT] Failed JSON contract`).
3. **Proceed:** Move cleanly to the next candidate in the queue.

## 16.12 Operational Rule for Cron & Agent Execution

When processing channels:
1. Execute discovery and run scraper targets.
2. Route every record through the Data Quality Gate.
3. Pass valid candidates to `merge_to_crm()`.
4. Run a read-only post-merge validation pass confirming row column counts and UTF-8 integrity.
5. If any row corrupts the CSV structure, immediately revert the file to its pre-run state.

---

# 17. CRM DATA QUALITY GATE — MANDATORY ENFORCEMENT

The CRM Data Quality & CSV Formatting rules from Section 16 are mandatory for EVERY creator discovery, scraping, enrichment, and CRM merge operation.

No creator record may be written to `data/Creator-Intel-CRM-List.csv` until it has passed all applicable validation checks.

## 17.1 Mandatory Processing Order

1. Discover creator
2. Verify creator profile
3. Normalize platform, handle, name, and URL
4. Check duplicates against:
   - `data/input/input_channels.csv`
   - `data/Creator-Intel-CRM-List.csv`
5. Scrape using the approved scraper workflow
6. Validate scraped fields
7. Validate EvidenceJSON
8. Validate CSV-safe formatting
9. Validate column count/schema
10. Call the existing `merge_to_crm()` logic
11. Validate the CRM again after merge

## 17.2 Hard Rules

- **NEVER** bypass `merge_to_crm()`.
- **NEVER** manually append raw CSV rows.
- **NEVER** modify `data/input/input_channels.csv`.
- **NEVER** invent missing creator information.
- **NEVER** insert uncertain or malformed records.
- **NEVER** allow invalid JSON into `EvidenceJSON`.
- **NEVER** allow a row with an incorrect column count into the CRM.
- **NEVER** allow search-result URLs to enter the CRM.
- **NEVER** overwrite verified CRM values unnecessarily.

## 17.3 Failure Protocol

If a record fails validation:
```
REJECT → LOG REASON → SKIP RECORD → CONTINUE
```

Do not "fix" uncertain information by guessing.

## 17.4 Cron Execution

For cron execution, the same rules apply to every run. Each scheduled run must independently validate every record through the full Data Quality Gate before any merge_to_crm() call.

---

# 18. OUTPUT FORMATTING STANDARD

All platform scrapers must enforce these formatting rules **before any row is merged into the CRM**, regardless of platform. These rules are mandatory for every scrape, discovery, and merge operation.

## 18.1 Follower Count Normalization

- Always normalize to English **K/M/B notation** regardless of platform locale.
  - `"1.1J"` (Malay: juta = million) → `"1.1M"`
  - `"pengikut"` / `"mengikuti"` labels → stripped/ignored
  - Plain numbers → auto-convert (e.g., `26,737` → `"26.7K"`, `1,108,428` → `"1.1M"`)
- **Never** write a locale-specific number or label directly into the `FollowerCount` column.
- **Raw/original value** goes into `EvidenceJSON.follower_raw_locale` for traceability only.

Use the shared helper: `normalize_follower_to_kmb(raw)` from `code/scraper/common.py`.

## 18.2 Bio/Preview Text Cleanup

- Strip **platform UI chrome** from bio/preview text for **every platform**, not just Facebook:
  - Malay/Indonesian tokens: `Lagi`, `Siaran`, `Perihal`, `Reels`, `Foto`, `Pengenalan`, `mengikuti`, `pengikut`
  - Multi-language nav tabs: `More`, `See More`, `Ver más`, `En savoir plus`, `Meer lezen`, `Voir plus`
  - Cookie/consent banners: `Cookie`, `Accept`, `Consent`
- Always produce a **single clean snippet/sentence** — no multi-line menu fragments.
- Collapse whitespace/newlines to a single trimmed line using `clean_platform_ui_text(text)`.
- Store the cleaned version in `bio_preview` and `Notes`; the raw original goes into `EvidenceJSON` only.

Use the shared helper: `clean_platform_ui_text(text)` from `code/scraper/common.py`.

## 18.3 Locale Consistency

- **Force English (en-US) locale** + `Accept-Language: en-US,en;q=0.9` on **every** Playwright browser session, for **every platform** scraper.
- This prevents scraped UI text from being returned in another language (Malay, Indonesian, Spanish, French, etc.).
- Use the shared helper: `create_english_context(browser)` from `code/scraper/common.py`.
- Non-browser scrapers (YouTube via yt-dlp, Vimeo via yt-dlp, Civitai via API) are not affected by browser locale but must still normalize follower counts and clean bio text.

## 18.4 Link Resolution

- Always resolve `external_link` / `SampleContentURL` to the **final real URL**.
- Decode any **URL-encoded/double-wrapped links** before saving.
  - e.g. `https://www.instagram.com/https%3A%2F%2Fwww.instagram.com%2Fhandle%2F` → `https://www.instagram.com/handle/`
  - e.g. Facebook redirect `l.facebook.com/l.php?u=...` → decoded target URL
- Use the shared helper: `resolve_final_url(url)` from `code/scraper/common.py`.

## 18.5 Record Completeness Gate

- **Never** merge a "discovery-only" or partially-scraped record (missing `follower_count` AND `bio_preview`) into the main CRM, **regardless of platform**.
- Route incomplete records to a separate **pending-review queue** (`data/pending_review.csv`) instead.
- This is enforced by `is_discovery_only()` and `route_to_pending_review()` in `code/scraper/common.py`, called automatically by `merge_to_crm()`.
- The pending-review queue is for manual review — these records must NOT pollute the Master CRM.

## 18.6 Validation on Every Merge

- Run the existing **Data Quality Gate** (AGENTS.md Sections 16-17) on **every** `merge_to_crm()` call, no exceptions per platform:
  - Schema: 19 columns, exact column count
  - Normalization: K/M/B follower format, clean bio text
  - Dedup: case-insensitive ProfileURL match
  - EvidenceJSON: valid RFC 8259 JSON
  - CSV encoding: UTF-8, no BOM, no embedded newlines
  - No Malay/foreign UI contamination in Notes
- On failure: `REJECT → LOG REASON → SKIP RECORD → CONTINUE`.

## 18.7 Cross-Platform Application

These rules apply to all platform scrapers:
- **TikTok** (`code/scraper/tiktok.py`)
- **Instagram** (`code/scraper/instagram.py`)
- **Facebook** (`code/scraper/facebook.py`)
- **LinkedIn** (`code/scraper/linkedin.py`)
- **Reddit** (`code/scraper/reddit.py`)
- **Threads** (`code/scraper/threads.py`)
- **YouTube** (`code/scraper/main.py`) — non-browser, yt-dlp based
- **Vimeo** (`code/scraper/vimeo.py`) — non-browser, yt-dlp based
- **Civitai** (`code/scraper/civitai.py`) — non-browser, API based
- **Batch dispatcher** (`code/scraper/run.py`, `code/scraper/scrape_all.py`) — uses `create_english_context()` for all Playwright sessions

---

# 19. GOOGLE SHEETS INTEGRATION (OPTIONAL)

An optional Google Sheets sync step runs automatically after `merge_to_crm()` succeeds, configured entirely via `.env`.

## Setup

1. Enable Google Sheets API in Google Cloud Console
2. Create a Service Account and download the JSON key file
3. Share the target Google Sheet with the service account email address
4. Set in `.env`:
   - `GOOGLE_SHEETS_ENABLED=true`
   - `GOOGLE_SHEETS_CREDENTIALS_PATH=/path/to/service-account.json`
   - `GOOGLE_SHEET_ID=<spreadsheet-id>`
   - `GOOGLE_SHEET_TAB=Temp`

## Behavior

- After every successful CRM merge, `sync_crm_to_sheet()` is called with the newly merged/updated rows only
- If credentials are missing, invalid, or the API call errors out: logged and skipped — **never blocks the scrape**
- Only fully validated CRM rows are synced (pending_review records are excluded)
- Module: `code/scraper/sheets_sync.py`
- Library: `gspread` + `google-auth` (added to `requirements.txt`)
