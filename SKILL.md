---
name: creator-research-system
description: Safe, verifiable workflow for discovering, scraping, classifying, and organizing publicly available information about content creators (or any similar public-data research subject) into a master CRM/dataset and a knowledge base like Obsidian. Use this whenever the user asks to discover/find new creators, scrape a platform, refresh creator data, sync results to a knowledge base, or check on a research/CRM pipeline's data integrity. Enforces strict rules against fabricating data and destroying existing records — trigger this any time an operation could append to, update, or overwrite a CSV/dataset that accumulates over time.
---

# Creator Research System

A safety-first workflow for building and maintaining a research dataset
(e.g. AI content creators, or any similar public-data subject) through
repeated discovery and scraping runs, without ever silently losing or
inventing data.

The skill is generic — the actual project facts (file paths, which
platforms are supported, what tech stack runs the scrapers, the CRM
schema) live in `AGENTS.md`, which the user fills in for their own
project. Never hardcode a specific project's paths, platform list, or
schema into this file.

## Why this exists

A research CRM that accumulates data over many sessions is only useful
if every session can trust what's already there. The two failure modes
this skill exists to prevent:

1. **Silent data loss** — a "refresh" or "update" accidentally replacing
   an entire dataset instead of merging into it.
2. **Silent fabrication** — filling in a plausible-looking value (a
   follower count, an email, a location) that was never actually
   verified, because it makes the output look more complete.

Both are worse than an incomplete or slow result, because they corrupt
trust in the dataset for every future session, not just this one.

## First-time setup

If the repo doesn't yet have an `AGENTS.md` at its root, walk the user
through creating one from `assets/AGENTS-template.md`. Ask for:

1. What the research subject is (e.g. "AI content creators", but this
   generalizes to any similar public-data research)
2. Which platforms/sources are supported and where each scraper lives
3. Where the authoritative/master dataset file(s) live, and their schema
4. Where the input queue (if separate from the master dataset) lives
5. Whether there's a knowledge-base sync step (Obsidian or similar) and
   its folder structure
6. Any project-specific classification categories or tags

Save their answers into `AGENTS.md`. Read it at the start of every
session that touches this workflow — don't ask again once it exists.

## Critical rules — these override everything else

### Never destroy master data

Any file the user's `AGENTS.md` marks as authoritative/master data must
never be deleted, replaced, truncated, or recreated from only the
latest run's results. Default behavior is always:

```
PRESERVE EXISTING DATA → DEDUPLICATE → APPEND NEW DATA → VERIFY
```

If there's any uncertainty about whether an operation ("update",
"sync", "refresh", "save", "rebuild", "regenerate") means merging or
replacing, stop before writing and ask the user. Never assume "refresh"
means "start over."

### Never fabricate

Never guess or invent: names, handles, follower counts, emails,
locations, languages, tools used, profile URLs, content URLs,
engagement metrics, or any other field an entry is supposed to hold.
Use an explicit `Unknown` (or whatever placeholder the project's schema
uses) when information can't be verified — never a plausible-sounding
guess.

### Never claim completion without verification

Don't say a task is "complete" until every required step has actually
been verified to have happened — the dataset was re-read after saving,
the record count checked, the sync step confirmed. If a step fails,
report the failure plainly instead of claiming success anyway.

### Discovery and scraping are separate

- **Discovery** finds new subjects (via search or public directories)
  and adds them to the input queue. It does not run scrapers.
- **Scraping** reads the input queue and extracts data for entries
  already in it. It does not perform new discovery.

Only combine the two when the user explicitly asks for both in the same
request. A request for one should never silently trigger the other.

## Discovery workflow

Trigger only on explicit requests to discover/find/search for new
subjects — never automatically during a routine scrape.

```
SEARCH
    ↓
VERIFY SUBJECT (real, matches the research focus)
    ↓
VERIFY PROFILE/SOURCE URL
    ↓
CHECK FOR DUPLICATES (input queue + master dataset + knowledge base)
    ↓
APPEND TO INPUT QUEUE
    ↓
APPEND/UPDATE MASTER DATASET
    ↓
CREATE/UPDATE KNOWLEDGE-BASE NOTE (if applicable)
    ↓
UPDATE DAILY/SESSION LOG (if the project keeps one)
    ↓
VERIFY EVERYTHING
    ↓
REPORT
```

**Duplicate check, before adding anything:** compare the strongest
available identifier (a profile URL beats a name), search the master
dataset, search the knowledge base if there is one. If it already
exists, don't add a second row — update the existing record if there's
new verified information, and report that it already existed instead of
silently skipping it.

**When the user asks for N new subjects:** N means N genuinely new,
deduplicated, verified additions — existing or duplicate hits don't
count toward N. Keep going until N qualifying additions are made, and
report candidates reviewed, duplicates skipped, and rejected candidates
alongside the count actually added.

## Scraping/extraction workflow

Trigger only on explicit requests to scrape/extract/refresh data for a
given source — never perform new discovery during this step.

```
READ INPUT QUEUE
    ↓
FILTER TO REQUESTED SOURCE
    ↓
RUN EXTRACTION
    ↓
SAVE RAW OUTPUT (intermediate — not the master dataset)
    ↓
VERIFY OUTPUT
    ↓
MERGE INTO MASTER DATASET (see "Master dataset update" below)
    ↓
SYNC KNOWLEDGE BASE (if applicable)
    ↓
VERIFY EVERYTHING
    ↓
REPORT
```

### Master dataset update

For every record in the fresh output:

1. Check whether it already exists in the master dataset (by the
   strongest identifier available).
2. If it exists → update the existing row with the new verified
   information. Never blank an existing field just because this run
   returned nothing for it, and never overwrite verified data with
   `Unknown`.
3. If it doesn't exist → append a new row.
4. Never replace the entire master dataset with this run's output.

**Data priority when the same field has multiple sources:** prefer the
newest *verified* value over an older one, but never let a failed or
empty result from a new run overwrite a previously verified value.

```
CURRENT VERIFIED RUN → PREVIOUS VERIFIED RUN → DISCOVERY-STAGE DATA → OLD EXISTING DATA
```

## Safe write procedure

Before modifying any master/authoritative file:

1. Confirm the file exists and read its current contents.
2. Record the current row/entry count.
3. Apply the intended append/update in memory first.
4. Validate the resulting dataset (schema, column order, no unexpected
   loss).
5. Write the update.
6. Re-read the saved file and verify: previous count preserved, new
   records present, columns/schema unchanged, nothing unexpectedly
   removed.
7. Report: previous count, new entries found, duplicates skipped,
   entries added, final count.

If validation fails at any point, don't overwrite the original — leave
it intact and report what went wrong.

Never delete existing records unless the user explicitly names the
specific record(s) to delete from the specific file. Absent that,
existing records are protected by default.

## Data quality and evidence

Distinguish between:
- **Verified** — directly confirmed from a public source
- **Extracted** — pulled from source content as-is
- **AI-generated analysis** — inference from available data, not itself
  evidence
- **Reasonable inference** — a logical deduction from verified facts,
  labeled as such
- **Unknown** — genuinely unverifiable

Attach evidence (a source URL, a verified-at date) to important fields
where the project's schema supports it. Don't present AI-generated
analysis as if it were a verified fact, and don't invent citations or
sources.

Only collect information that's publicly accessible. Never access
private accounts, private information, or anything requiring
credentials the subject hasn't made public.

## Error handling

When something fails:
1. Read the full error, identify the actual cause.
2. Determine whether it's temporary or permanent.
3. Make the smallest appropriate fix and retest.
4. If a specific record couldn't be processed, don't silently treat it
   as succeeded — preserve the original input record, mark it as
   failed, note why, and continue with the rest.
5. Report successful and failed counts together, never just the
   successes.

## Reporting

Report completed work with a clear structure that separates what
actually happened from what's still open:

```
Completed:
- [what was found/processed/added, with counts]

Issues:
- [anything that failed or couldn't be verified]

Next steps:
- [what the user might want to do next]
```

Never blur "found" into "verified" into "added" — a candidate that was
found but not verified, or verified but not added (duplicate), should
be reported as such rather than folded into a single success count.

## Knowledge-base sync (if the project uses one, e.g. Obsidian)

If `AGENTS.md` defines a knowledge-base structure, sync into it after
every discovery or scraping run:
- One note per subject — search for an existing note before creating a
  new one; update rather than duplicate.
- Clearly distinguish discovered information from scraped information
  in the note — don't present one as the other.
- A session/daily log entry recording what happened in that run.
- Cross-link related notes where the project's convention supports it.

Never write outside the knowledge-base directory the project defines,
and never create a second knowledge base.

## Version control and secrets

If the project uses git: review changes before committing, and never
commit API keys, passwords, tokens, cookies, session data, or other
credentials. Use environment variables or the project's secret-storage
convention instead, and make sure `.gitignore` covers the master
dataset and any files containing real subject data if the repo is
meant to be shared.

## Reference files

- `assets/AGENTS-template.md` — template for a new project's AGENTS.md
- `references/data-integrity-checklist.md` — the full pre-completion
  checklist for discovery and scraping runs
