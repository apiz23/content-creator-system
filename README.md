# Creator Research System

Discover, scrape, classify, and organize publicly available information about AI/generative AI content creators across platforms. Outputs structured CSVs and syncs to an Obsidian vault.

## What it does

- **Discovery** — find new AI creators via web search, verify profiles, check for duplicates, add to input queue
- **Scraping** — run platform-specific scrapers (TikTok, Instagram, YouTube, etc.) to extract follower counts, bios, emails, and AIGC classification
- **Classification** — AI tools like Ollama classify creators by tags, primary AI tool, AIGC verdict, language
- **Sync** — after every scrape, update the Master CRM, creator Obsidian notes, platform notes, and daily logs

## Project structure

```
Creator-Research-System/
├── Code/scraper/          # Platform scrapers (tiktok.py, instagram.py, etc.)
├── data/
│   ├── input/input_channels.csv    # Persistent scraping queue
│   ├── output/                    # Scraper output CSVs
│   └── Creator-Intel-CRM-List.csv # Master CRM database
├── obsidian/Creator Research/     # Obsidian vault (Creators, Platforms, Daily, etc.)
├── analysis/                      # Analysis outputs
└── AGENTS.md                      # Workflow rules and guidelines
```

## Supported platforms

- TikTok — Playwright + Ollama classifier
- Instagram
- YouTube
- Threads
- Facebook
- LinkedIn
- Reddit
- Vimeo
- Civitai

## Quick start

```bash
# Activate venv
source .venv/bin/activate

# Scrape TikTok
python Code/scraper/tiktok.py

# Other platforms
python Code/scraper/instagram.py
python Code/scraper/youtube.py
# etc.
```

## Rules

- Never overwrite or delete master data — always append/update
- Never fabricate creator information — use `Unknown` when unverifiable
- Discovery and scraping are separate workflows
- Obsidian sync happens automatically after every scrape
- See `AGENTS.md` for full workflow details

## Tech stack

- Python 3
- Playwright (browser scraping)
- Ollama + qwen3.5:latest (local AI classification)
- Pandas (CSV processing)
- Obsidian (knowledge base)

## Environment

Create a `.env` file if needed for API keys (currently not required for core scraping).

## License

Private — not published.
