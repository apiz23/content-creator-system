# Creator Research System — Agent Workflow

A safety-first agent workflow for building and maintaining a research
dataset (in this case, publicly available information about AI content
creators) through repeated discovery and scraping runs, without ever
silently losing or fabricating data.

This is the generalized version of the internal `AGENTS.md` used to run
the actual project — the real project's file paths, platform list, CRM
schema, and scraper code stay private. What's here is the reusable
*procedure*: the rules that make a long-running, multi-session research
pipeline trustworthy.

## Why this exists

A dataset that accumulates over many sessions is only as good as the
guarantees around each session's writes to it. Two failure modes this
workflow is built to prevent:

- **Silent data loss** — a "refresh" or "sync" accidentally replacing an
  entire dataset instead of merging into it.
- **Silent fabrication** — an agent filling in a plausible-looking value
  (a follower count, a location, an email) that was never actually
  verified, just to make output look complete.

The rules in `SKILL.md` exist specifically to make both of those hard to
do by accident.

## What's in this repo

```text
creator-research-skill/
├── SKILL.md                              ← the full procedure
├── assets/
│   └── AGENTS-template.md                ← template for a new project's facts
└── references/
    ├── data-integrity-checklist.md       ← pre-completion verification checklist
    └── scraping-patterns.md              ← worked example of scraper engineering conventions
```

- **`SKILL.md`** — the generic procedure: discovery vs. scraping
  separation, the append-not-replace rule for master data, the
  no-fabrication rule, the safe-write verification steps, error
  handling, and reporting format. Doesn't reference this project's real
  paths or schema.
- **`AGENTS-template.md`** — what a real project fills in: the actual
  file paths, supported sources, tech stack, and schema. The real,
  filled-in version (with this project's actual CRM paths, platform
  scrapers, and Obsidian structure) is kept private.

## The core discipline, in short

1. **Discovery and scraping are separate operations.** Discovery finds
   new subjects and queues them; scraping extracts data for subjects
   already queued. Neither triggers the other unless explicitly asked.
2. **Master data is append-only by default.** Every write to an
   authoritative dataset follows: preserve existing data → deduplicate →
   append new data → verify. "Replace" is never assumed from words like
   "update," "refresh," or "sync."
3. **Nothing is fabricated.** Unverifiable fields are marked `Unknown`,
   never filled with a plausible guess.
4. **Completion requires verification, not just execution.** A run isn't
   reported as complete until the write has been re-read from disk and
   the counts checked — see `references/data-integrity-checklist.md`.
5. **Failures are reported, not hidden.** A record that couldn't be
   processed is preserved and marked as failed, not silently dropped
   from the count.

## Applying this to another project

This pattern generalizes to any project where an agent is repeatedly
appending to a dataset from external sources — not just creator
research. To adapt it:

1. Copy `assets/AGENTS-template.md` to `AGENTS.md` and fill in your
   project's real paths, sources, tech stack, and schema.
2. Drop `SKILL.md` and `references/` into the project as-is.
3. Point your agent tool at both files (see your tool's docs for how it
   discovers/loads instructions and skills).

## Status

This is a generalized, sanitized version of an active internal project
for sharing with a supervisor/reviewer. It intentionally excludes the
real scraper code, CRM data, and knowledge-base contents.
