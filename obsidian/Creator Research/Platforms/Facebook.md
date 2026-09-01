# Facebook

## Overview

- **Official URL:** https://facebook.com
- **Scraper:** Code/scraper/facebook.py (Playwright + Ollama local LLM classifier)
- **Scrape Date:** 2026-09-01 (batch 3: 3/5 scraped)
- **Input Records:** 62 Facebook profiles from data/input/input_channels.csv
- **Output Records:** 52 rows (some profiles have both page-level and post-level entries)
- **Unique Creators:** 44 + 3 batch 3 = 47 scraped creators

## Fields Extracted

- ProfileURL
- Name/Handle
- Platform
- FollowerCount
- Email
- Tags
- OutreachStatus
- LastScrapedAt
- Region
- Language
- PrimaryAITool
- SampleContentURL
- AIGCVerdict
- DiscoveredAt
- Source
- Notes
- FeedURL
- ContactSourceURL
- EvidenceJSON

## Extraction Method

- Headless Chromium via Playwright
- OpenGraph meta tags (og:title, og:description)
- Body text parsing for follower counts
- Local LLM (Ollama qwen3.5:latest) for AI classification
- Regex fallback for email and AI tool detection
- 2-second delay between profiles to avoid IP throttling

## Known Limitations

- Facebook profile access is partially gated — some pages return limited public data without login
- Follower counts extracted from og:description or body text may use localized terms (e.g., "pengikut" for Indonesian)
- Some profiles are discovery-only and have minimal public information
- Email addresses rarely exposed in public Facebook profiles
- Batch 3: 2 of 5 profiles (R3DZ3RO, AitanaLopezAI) timed out — likely gated/personal pages requiring login

## Creator Notes (Scraped)

47 creator notes from all Facebook scrape batches:

### Batch 1+2 (2026-08-27)
- [[sciencenaturepage]] — Hashem Al-Ghaili (34M, hybrid, Sora)
- [[aljazeera]] — Al Jazeera English (22M, no, Sora)
- [[kub-yaj]] — Kou Yang / KouYangAI (3.1M, yes, Kling)
- [[abcnews]] — ABC News (18M, yes, Sora)
- [[techcrunch]] — TechCrunch (2.9M, no, GenAI)
- [[owwstin]] — Austin Armstrong / Syllaby.io (2.1M, hybrid, ChatGPT)
- [[mkbhd]] — Marques Brownlee (1.4M, hybrid, ChatGPT)
- [[tombilyeu]] — Tom Bilyeu / Impact Theory (1.3M, hybrid, GenAI)
- [[fastcompany]] — Fast Company (1.2M, no, GenAI)
- [[newschannel5]] — NewsChannel 5 Nashville (1.2M, no, Sora)
- [[muddaseraltaf]] — Muddaser Altaf (1.1M, hybrid, GenAI)
- [[duekneel]] — duekneel (557K, yes, GenAI)
- [[nasirushamim]] — Nasir Uddin Shamim (492K, yes, Runway)
- [[filmmakingmasterclass]] — Blake Ridder (380K, hybrid, GenAI)
- [[kevinstratvertyoutube]] — Kevin Stratvert (340K, hybrid, GenAI)
- [[kdjayakodypro]] — K.D. Jayakody (275K, yes, Midjourney)
- [[marismith]] — Mari Smith (254K, hybrid, Sora)
- [[renderforest]] — Renderforest (249K, yes, Sora)
- [[tylerbernabe]] — Tyler Bernabe / jboogxcreative (201K, yes, GenAI)
- [[aniksingal]] — Anik Singal (175K, hybrid, Runway)
- [[carter-braydon]] — Braydon Carter (146K, hybrid, ChatGPT)
- [[cinednews]] — CineD (138K, hybrid, Midjourney)
- [[aisavvy]] — AI Savvy (114K, yes, Runway)
- [[frenchiebles]] — Frenchiebles (47K, hybrid, Runway)
- [[talhaashraf01]] — Talha Ashraf (31K, yes, Veo)
- [[kirk-carlson-2025]] — Kirk Carlson (31K, hybrid, ChatGPT)
- [[moochuumalaysia]] — Moo Chuu Malaysia (56K, hybrid, GenAI)
- [[themustafatalks]] — The Mustafa talks (26K, hybrid, Veo)
- [[golden-czermak-official]] — Golden Czermak / FuriousFotog (19K, hybrid, ChatGPT)
- [[joni-gutierrez]] — Joni Gutierrez (3.2K, hybrid, ChatGPT)
- [[blair-adams]] — Blair Adams (2.1K, hybrid, Runway)
- [[shimira]] — Shimira Cole / MiraCole (2.1K, hybrid, ChatGPT)
- [[mausampuriedu]] — Mausam Puri (1.2K, hybrid, GenAI)
- [[blueeyesinfosoft]] — Blue Eyes Infosoft (1.7K, yes, Runway)
- [[runwayml]] — Runway Applied AI Research (4K, yes, Runway)
- [[blog]] — Meta Official Blog (N/A, hybrid, Meta AI)
- [[serviceclickcorporation]] — AI Video Creator Arlington TN (53 likes, hybrid, GenAI)
- [[100083241103501]] — Technology IG (230K, hybrid, Sora)
- [[100090113973595]] — Tech Toil | Moradabad (79K, hybrid, Veo)
- [[100095042125983]] — Professor Casey (26K, yes, GenAI)
- [[61589152383467]] — M.E. Owens (15K, yes, GenAI)
- [[61590531123270]] — Ai video creator (40, yes, GenAI)
- [[61591641855684]] — AI video creator (14, yes, GenAI)
- [[avi-bandyopadhyay]] — Avi Bandyopadhyay (5.8K, hybrid, GenAI)

### Batch 3 Scraped (2026-09-01)
- [[nightcafestudio]] — NightCafe (N/A followers, hybrid, GenAI, Instagram: @nightcafestudio)
- [[autumnskyeart]] — Autumn Skye ART (N/A followers, hybrid, GenAI)
- [[imma-ai]] — Imma (N/A followers, hybrid, GenAI) — scraped page title: Maira Alvarenga

### Batch 3 Failed (2 gated pages)
- [[r3dz3ro]] — R3DZ3RO / Zerro — scraper timed out, og:title not found
- [[aitanaai]] — Aitana Lopez AI — scraper timed out, og:title not found

Total Facebook creators in system: 62 input profiles / 47 scraped creators

## AIGC Distribution

- **yes:** 19 profiles — public AI creators/filmmakers, exclusively AI-generated content (batches 1+2)
- **hybrid:** 25 profiles — mix of AI and non-AI content, or AI tool discussion (23 from batches 1+2 + 3 from batch 3 — all batch 3 scraped as hybrid)
- **no:** 3 profiles — news/media brands without clear AI focus (aljazeera, fastcompany, techcrunch, newschannel5)

Note: Some large media accounts were captured because they appeared in SearXNG searches for AI video/filmmaker terms on Facebook.

## Related

- [[Creator Research System]]
- [[2026-09-01]]
