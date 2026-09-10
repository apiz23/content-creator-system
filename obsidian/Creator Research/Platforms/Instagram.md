---
name: Instagram
platform: Instagram
type: Social Media Platform
status: Active
last_discovery: 2026-09-09
last_scrape: 2026-09-03
---

# Instagram

## Overview

Visual-first social platform. Strong AI art and AI filmmaking creator community. Meta-owned.

## Discovery (2026-09-03)

Discovered 4 new Instagram creators via FeedSpot Top 40 AI Artists Instagram Influencers 2026:

- [[@troplanduniverse]] — Josh Gottsegen, AI wildlife art, 984K followers, 1.5B+ views (Macro). Featured by Meta, Adobe, OpenAI.
- [[@rowan_lewgalon_aiart]] — Rowan, AI artist, Nightcafe Studio Ambassador, 118.6K followers (Macro)
- [[@juliewdesign]] — Julie W. Design, traditional + generative AI art, 25.3K followers, +22% growth (Micro)
- [[@poetofcode]] — Dr. Joy Buolamwini, AI ethics leader, MIT PhD, Algorithmic Justice League founder, 33.5K followers (Micro)

## Discovery (2026-09-09)

Discovered 5 new Instagram creators via FeedSpot, Kolsquare, The Daring Creators, and Hyax:

- [[@troplanduniverse]] — Josh Gottsegen, AI wildlife/cinematic art, 1.4M followers, collaborations with Meta, Adobe, OpenAI, Sora, Kling
- [[@annawessenart]] — Anna Wessen, Visual Artist | AI Creative Director, 62.5K followers, Los Angeles
- [[@grannyspills]] — AI-generated 75-year-old influencer by Blur Studios, 2M followers, Veo3, luxury lifestyle
- [[@fit_aitana]] — Aitana Lopez, Spanish AI fashion influencer, 404K followers, created by The Clueless Agency
- [[@surreailist]] — Lukas Nowacki, "psychological descents" AI films, Berlin Music Video Awards 2026 jury, Kinovi AI

## Discovery (2026-09-04)

Discovered 5 new Instagram creators via FeedSpot Top 40 AI Artists Instagram Influencers 2026:

- [[@iva_ai_popsurreal]] — Suzan Valois, AI pop surrealism art, 378.6K followers (Macro)
- [[@jakeelwes]] — Jake Elwes, queer AI media art & deepfake drag, London, 61.8K followers (Micro). Exhibited at V&A, Pinakothek, ZKM.
- [[@sofiacrespo]] — Sofia Crespo, generative biology AI art, 1/2 of @entangledothers, 61.1K followers (Micro)
- [[@sougwen]] — Sougwen Chung, AI robotics art, human-robot drawing, founder Studio Sclicitent, 51.3K followers (Micro). Guggenheim, V&A exhibitions.
- [[@amy.aiart]] — Amy Truong, Midjourney dark fantasy & witch AI art, tarot deck author, 36K followers (Micro)

## Scrape (2026-09-03)

**Scraper:** `Code/scraper/instagram.py` (Playwright + Ollama qwen3.5)
**Input:** `data/input/input_channels.csv` (Instagram rows)
**Output:** `data/output/instagram_scraped_output.csv`

**Records processed:** 57
**Successfully scraped:** 57 (54 with follower counts, 3 unavailable)
**Failed:** 0

### Scraped Creator Highlights

#### AI Filmmakers
| Handle | Followers | AIGC |
|--------|-----------|------|
| @dariondanjou | 5,566 | hybrid |
| @ai_anav | 18,800 | yes |
| @kseniia_saraieva | 2,190 | yes |
| @theaifilmmaker | N/A | yes |
| @ai__filmmaker | N/A | yes |
| @ai.filmmaker | N/A | yes |
| @ai_mov_director | N/A | yes |
| @lam.aifilm | N/A | yes |
| @ai_daniels | N/A | yes |
| @theunusualfilmmaker | N/A | yes |
| @surajrewadia | N/A | yes |
| @theblasian | N/A | yes |
| @sora2kavo | N/A | yes |
| @despicable.ai | N/A | yes |
| @katsukokoiso.ai | N/A | yes |
| @trashcanroxanne | N/A | yes |
| @joby_thuruthel | N/A | yes |
| @fiqri_fox | N/A | yes |

#### AI Art / Visual Artists
| Handle | Followers | AIGC |
|--------|-----------|------|
| @troplanduniverse | 1M+ | yes |
| @emilypellegrini | 547.3K | yes |
| @hannamalkova | 356.1K | yes |
| @jocelincarmes | N/A | yes |
| @cy_artsfun | 117K | yes |
| @tarynsouthern | 106K | yes |
| @aditi.aimuse | N/A | yes |
| @quasimondo | N/A | yes |
| @amos_winikoff | N/A | yes |
| @sergioalbiac | N/A | yes |
| @pixlpa | N/A | yes |
| @barbara.chira.ai.art | N/A | yes |
| @jas___black | N/A | yes |
| @art.bypavlidiy | N/A | yes |
| @naamachen1 | N/A | yes |
| @purdyjoy0 | N/A | yes |
| @robertrgaudette | N/A | yes |
| @xwell__media | N/A | yes |
| @aiartoriginal | N/A | yes |
| @volcano.visuals | N/A | yes |
| @ai_flime | N/A | yes |
| @lenoty_ai | N/A | yes |
| @techprophett | N/A | yes |
| @dvsmethid | N/A | yes |
| @ai_funcorner | N/A | yes |
| @aiesmars | N/A | yes |
| @alexmoonai | N/A | yes |
| @aicineguy | N/A | yes |
| @harry.motion | N/A | yes |
| @drunk_on_ink_atx | N/A | yes |
| @cavie2002 | N/A | yes |
| @avinashyap | N/A | yes |

#### Official AI Tool Accounts
| Handle | Followers | AIGC |
|--------|-----------|------|
| @soraofficial | N/A | yes |
| @runwayapp | N/A | yes |
| @klingai_official | N/A | yes |

### Notes

- 54 of 57 profiles returned follower counts via Playwright OG meta scraping.
- 3 profiles (@aiartoriginal, @ai_flime, @aiartoriginal dup) had no follower data — likely private or blocked.
- Ollama qwen3.5 used for AIGC classification — most classified as "yes".
- [[2026-09-03]]
