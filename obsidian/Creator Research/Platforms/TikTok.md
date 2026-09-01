---
type: platform
last_updated: 2026-09-01
---

# TikTok

## Overview

- **Official URL:** https://tiktok.com
- **Scraper:** Code/scraper/tiktok.py (Playwright + Ollama local LLM classifier)
- **Scrape Date:** 2026-09-01
- **Input Records:** 18 TikTok profiles from data/input/input_channels.csv
- **Output Records:** 18 rows
- **Unique Creators:** 18
- **Successfully Scraped:** 18
- **Failed:** 0

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
- `data-e2e="followers-count"` for follower count
- `data-e2e="user-bio"` for bio text
- `data-e2e="user-link"` for external bio link
- Local LLM (Ollama qwen3.5:latest) for AI classification
- Regex fallback for email and AI tool detection
- 2-second delay between profiles

## Known Limitations

- TikTok may show different content/UI based on region and login state
- Some profiles may require scrolling to load full follower counts
- Email extraction depends on bio text containing a valid email address
- Russian-language profiles (e.g., @egorkuzminxr) may have non-English bio content

## Creator Notes

### Newly Discovered & Scraped (2026-09-01)

- [[brandnat]] — Brand Nat / Natalie Choprasert (446.3K, AI Automation for Business, Australia, hello@brandnat.com)
- [[aicenturyclips]] — AI Century (431.9K, AI video clips, AI tools, Aicenturyinfo@gmail.com)
- [[tonyaube]] — Tony Aube (423.7K, AI design, ex-Google AI, Silicon Valley)
- [[kanekallaway]] — Kane Kallaway (433.9K, Tech & AI, content creation, sandcastles.ai)
- [[gianluca.mauro]] — Gianluca Mauro (171K, AI entrepreneur, AI Academy founder, Italy)

### Previously Scraped (2026-09-01)

- [[ai.for.real.life]] — AI videos and filmmaking (26.5K, yes, GenAI, stan.store/AiForRealLife)
- [[theaifilmmaker]] — Neal / AI Filmmaker (17.8K, yes, GenAI, neal@theaifilmmaker.co)
- [[egorkuzminxr]] — Egor Kuzmin (53.8K, hybrid, GenAI, t.me/EgorKuzminXR1)
- [[gazi-ai]] — Gazi Jarin / @gazi.ai (664.2K, yes, GenAI, beacons.ai/gazi.ai)
- [[rileybrown-ai]] — Riley Brown / @rileybrown.ai (636.6K, yes, GenAI, shop.genspark.ai/s/rileybrown)
- [[aisavvy]] — AI Savvy / @aisavvy (131.1K, yes, GenAI, aisavvy.net)
- [[nomadatoast]] — Nomad Atoast / @nomadatoast (336.8K, yes, GenAI, liinks.co/nomadatoast)
- [[fawziammache]] — Fawzi Ammache / @fawziammache (133.4K, yes, GenAI, futurewithfawzi.com/links)
- [[sineadbovell]] — Sinead Bovell (313.1K, hybrid, GenAI, substack.com/@sineadbovell)
- [[justinfineberg]] — Justin Fineberg (288.8K, yes, GenAI, linktr.ee/justinfineberg)
- [[andyhafell]] — Andy Hafell (224.5K, yes, GenAI)
- [[shedoesai]] — She Does AI (219.8K, yes, GenAI, www.shedoesai.com, hello@shedoesai.com)
- [[immadsal]] — Madeline Salazar / @immadsal (182.2K, yes, GenAI, pop.store/immadsal, immadsal@dulcedo.com)

Total TikTok creators in system: 18

## AIGC Distribution

- **yes:** 16 profiles
- **hybrid:** 2 profiles — @egorkuzminxr, @sineadbovell

## Related

- [[Creator Research System]]
- [[2026-09-01]]
