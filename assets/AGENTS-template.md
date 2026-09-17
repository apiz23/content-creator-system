# AGENTS.md — <Project Name>

This file holds **stable facts and expectations** for this project —
read every session. The reusable *procedure* (discovery/scraping rules,
data-integrity checks, safety rules) lives in `SKILL.md` instead — don't
duplicate that here, just the facts specific to this project.

## Purpose

What this project researches and why (e.g. "publicly available
information about AI content creators, focused on Generative AI, AI
video, and developer tools").

## Tech stack

- Agent / orchestration:
- Reasoning or classification model:
- Scraping / extraction language & tools:
- Knowledge base tool (if any):

## Authoritative files

| File | Purpose | Can replace? |
|------|---------|--------------|
| `data/input/<queue>.csv` | Persistent scraping queue | Never |
| `data/<master-dataset>.csv` | Master dataset | Never |
| `data/output/*.csv` | Latest run output | Yes — intermediate |

Add/remove rows to match your actual project structure.

## Supported sources / platforms

List each source and where its extraction logic lives, e.g.:

- Platform A → `code/scraper/platform_a.py`
- Platform B → `code/scraper/platform_b.py`

## Knowledge base structure (if used)

```text
<knowledge-base-root>/
├── Attachments/
├── <Subjects>/       # one note per researched subject
├── Daily/            # or Sessions/ — one log per run
├── Platforms/         # or Sources/ — one note per source
├── Projects/
└── Research/
```

## Schema / classification categories

Whatever fields or tags this project's master dataset and subject notes
use (e.g. category, language, region, tool used, status) — list them
here so entries stay consistent across sessions.

## Notes

Anything else worth knowing every session — quirks in a particular
source's data, known limitations, naming conventions.
