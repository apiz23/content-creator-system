---
type: research
platform: TikTok
date: 2026-09-01
status: completed
records: 3
---

# TikTok AIGC Research — 2026-09-01

## Summary
Scraped 3 TikTok profiles from `data/input/input_channels.csv` using the existing TikTok scraper (`Code/scraper/tiktok.py`). All 3 profiles returned data and were saved to `data/output/tiktok_scraped_output.csv`. 3 Obsidian creator notes were updated in [[Creators]].

## Methodology
- Scraper: Playwright-based `tiktok.py` (existing, unmodified).
- Input: `data/input/input_channels.csv` (URLs containing `tiktok.com`).
- Extraction: `data-e2e` selectors for followers, bio, and external link.
- AI classification: Ollama fallback to rule-based keyword detection (GenAI/Sora).
- Follower counts extracted from `[data-e2e="followers-count"]` element text.

## Profiles Scraped

### @ai.for.real.life
- Followers: 26.5K
- Tags: AIGC, Sora
- Primary AI Tool: GenAI
- AIGC Verdict: yes
- Language: English
- External Link: stan.store/AiForRealLife
- Bio preview: "AI videos and filmmaking. Real workflows, cinematic storytelling, practical tools for creators."

### @theaifilmmaker
- Followers: 17.8K
- Tags: AIGC, Sora
- Primary AI Tool: GenAI
- AIGC Verdict: yes
- Language: English
- External Link: none extracted
- Bio preview: "Work sketch comedy 👉🏼 Send to your work bestie 🎬 neal@theaifilmmaker.co"

### @egorkuzminxr
- Followers: 53.8K
- Tags: AIGC, Sora
- Primary AI Tool: GenAI
- AIGC Verdict: hybrid
- Language: English (Russian name: Egor Kuzmin)
- External Link: t.me/EgorKuzminXR1
- Bio preview: "Егор Kuzmin | Специалист по нейросетям"

## Key Findings
- All 3 TikTok creators tagged with AIGC and Sora.
- Two classified as "yes" (AI-generated content), one as "hybrid" (@egorkuzminxr).
- Two have external links (Stan Store, Telegram); one had no link extracted.
- No public emails exposed in profiles (though @theaifilmmaker bio contains neal@theaifilmmaker.co inline).
- Total reach: ~98K followers across 3 profiles.

## Crawl4AI Test
- Crawl4AI 0.9.3 was also tested against TikTok profiles on 2026-09-01.
- Result: Blocked by anti-bot protection (`minimal_text` error, status 301).
- TikTok's anti-bot defenses block both Playwright and Crawl4AI equally.
- Conclusion: Crawl4AI does not provide an advantage over Playwright for TikTok scraping at this time.

## Related
- [[Creator Research]]
- [[TikTok]]
- [[2026-09-01]]
- `data/output/tiktok_scraped_output.csv`
