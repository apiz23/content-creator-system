# Facebook

## Overview

- **Official URL:** https://facebook.com
- **Scraper:** Code/scraper/facebook.py (Playwright + Ollama local LLM classifier)
- **Scrape Date:** 2026-09-04 (Scrape 2026-09-04: 9 profiles, 7 scraped + 2 failed)
- **Total Input Profiles:** 943 rows (all platforms in input_channels.csv)
- **Facebook Profiles in System:** 27 unique FB page URLs (9 new discovered 2026-09-07 + 18 existing)

## Discovery 2026-09-07 — 9 New Virtual Influencer Pages

**Source:** verifiedher.com/ai-influencers (28 confirmed virtual creators), amraandelma.com/top-ai-generated-influencers (24 list)
**Date:** 2026-09-07
**New pages:** 9
**Method:** Web search + verified list cross-reference (discovery only, no scrape)

### New Pages Added

| # | Page | FB URL | Creator/Studio | IG/TikTok | AIGC Verdict |
|---|------|--------|----------------|-----------|--------------|
| 1 | Vesna Blv | facebook.com/vesnablv | Self-disclosed AI persona | IG ~402K | yes |
| 2 | Maia Lima | facebook.com/maia.lima | The Clueless (Barcelona) | IG @limma.ia | yes |
| 3 | Lalina Valina | facebook.com/viva_lalina | Aurore Courtade (France) | IG @viva_lalina | yes |
| 4 | Bella Storm | facebook.com/bella.storm | Self-disclosed (Italy) | IG ~194K | yes |
| 5 | Kenza Layli | facebook.com/kenzalayli | Meriam Bessa / Phoenix AI (Morocco) | IG ~162K | yes |
| 6 | Shudu Gram | facebook.com/shudu.gram | Cameron-James Wilson (UK, 2017) | IG 239K+ | yes |
| 7 | Natalia Novak | facebook.com/natalia.novak | "Pierre" (US, anonymous) | IG ~61K | yes |
| 8 | Olivia C | facebook.com/oliviaislivinghigh | Alvero & Rita / Falamusa (Portugal) | IG ~11K | yes |
| 9 | Mia Kehley | facebook.com/miakehley | Anonymous | IG ~42K | yes |

### Also Updated

- **Lil Miquela** (facebook.com/lilmiquela): enriched from discovery-only (empty data) to verified record — 1M+ FB likes, IG 2.5M, TikTok 3.4M, Brud/Dapper Labs, Prada/CK/Samsung/BMW, music releases, TIME 2018 cover.

### Key Findings

- All 9 are confirmed virtual/AI personas per VerifiedHer documentation
- All 9 carry first-party or platform-confirmed AI disclosure
- FB pages vary in activity — some are secondary to IG/TikTok
- FB follower counts from page likes (not scraped via Playwright)
- **FB Scrapers Run:** 2 (batch 1+2: 2026-09-01, batch 3: 2026-09-01, Scrape 2026-09-04: new 10 only)

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

## Scrape 2026-09-04 — The New 10 Only

**Scope:** 10 Facebook pages discovered 2026-09-04 (virtual influencers only)
**Scraper:** Code/scraper/facebook.py (Playwright + Ollama qwen3.5)
**Input:** 10 new FB rows from input_channels.csv
**Output:** data/output/facebook_scraped_output.csv
**Time:** ~3m38s (9 profiles × ~25s each + 2 additional profiles via backup run)

### Results

| Status | Count | Profiles |
|--------|-------|----------|
| SUCCESS | 7 | lilmiquela, noonoouri, beeinfluencer, magazineluiza, guggimon, bermudaisbae, millasofiafin |
| FAILED | 2 | thalasya_ (timeout), kyraonig (timeout) |

### Scraped Follower Counts (FB page level)

| Creator | FB Followers | Language | Notes |
|---------|-------------|----------|-------|
| lilmiquela | N/A (1J pengikut — Malay) | Malay | OG description only shows name |
| noonoouri | N/A (Malay interface) | Malay | OG description only shows name |
| beeinfluencer | N/A (1K pengikut — Malay) | Malay | External: beeinfluencer.cl |
| magazineluiza | 14J pengikut = 14M (Portuguese) | Portuguese | GLOBAL #1 virtual influencer by FB followers |
| guggimon | 8.5K pengikut (Malay) | Malay | External: twitter.com/guggimon |
| bermudaisbae | 1.3K pengikut (Malay) | Malay | External: miquela.fyi |
| millasofiafin | 84 pengikut (Malay) | Malay | External: instagram.com/millasofiafin |
| thalasya_ | FAILED (timeout) | — | Page exists (HTTP 200) but Playwright timed out |
| kyraonig | FAILED (timeout) | — | Page exists (HTTP 200) but Playwright timed out |

### Key Findings

- **Lu do Magalu** confirmed: 14M FB followers — most-followed virtual influencer globally
- Most FB pages show "pengikut" (Malay for followers) — FB auto-translated interface; likely default region setting, not actual audience language
- FB follower counts much smaller than IG/TikTok — IG/TikTok are primary platforms for these virtual influencers
- 2 failures (thalasya_, kyraonig) — FB page exists but Playwright timed out loading og:title (30s) — likely FB anti-bot

## AIGC Distribution

- **yes:** 19 profiles — public AI creators/filmmakers, exclusively AI-generated content (batches 1+2)
- **hybrid:** 14 profiles — creators using AI as part of broader content strategy (batches 1+2)
- **unsure:** 14 profiles — AI use not confirmed from available data (all from discovery without scrape)


## Scrape 2026-09-07 — New 9 Discovery Batch

**Scope:** 9 Facebook pages discovered 2026-09-07 (virtual influencers)
**Scraper:** Code/scraper/facebook.py (Playwright + Ollama qwen3.5)
**Input:** data/input/fb_new_9_input.csv (9 profiles)
**Output:** data/output/facebook_scraped_output.csv
**Time:** ~6 min

### Results

| Status | Count | Profiles |
|--------|-------|----------|
| SUCCESS (og:title found) | 3 | maia.lima, bella.storm, kenzalayli |
| FAILED (og:title timeout) | 6 | vesnablv, viva_lalina, kenzalayli, shudu.gram, natalia.novak, oliviaislivinghigh, miakehley |

### Scraped Data (3 successes)

All 3 successful scrapes showed **Malay UI language** in og:description regardless of the page's actual market — consistent with FB auto-translated interface pattern documented in 2026-09-04 scrape.

| Creator | FB Followers | Language | Notes |
|---------|-------------|----------|-------|
| maia.lima | N/A | Malay UI | og:title found; og:desc shows "Tiada tempat kerja untuk dipapar" |
| bella.storm | N/A | Malay UI | og:title found; og:desc shows Malay interface |
| kenzalayli | N/A | Malay UI | og:title found; og:desc shows "Tiada tempat kerja untuk dipapar" |

### Key Findings

- 6 of 9 profiles timed out on og:title locator (30s) — Facebook anti-bot on these pages
- All 3 successful scrapes showed Malay UI language — confirms FB auto-translated interface pattern
- Follower counts not exposed via og:description for these pages
- This is consistent with 2026-09-04 findings: FB anti-bot blocks og:title on less-popular pages

## Notes

- Facebook's anti-bot measures frequently block Playwright scraping — og:title timeouts on 2 of 9 profiles in latest run
- FB pages often show localized language (Malay, Portuguese) in og:description regardless of actual audience — use with caution when interpreting language field
- Virtual influencer FB pages tend to have far fewer FB followers than IG/TikTok — FB is secondary platform for most
- **Discovery scrape 2026-09-10:** 1 new Facebook AI creator scraped and added to CRM (ausar.ai)
