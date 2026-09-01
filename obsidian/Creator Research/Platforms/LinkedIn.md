---
type: platform
last_updated: 2026-09-01
---

# LinkedIn

## Overview

- **Official URL:** https://linkedin.com
- **Scraper:** requests + OpenGraph meta extraction (HTTP-only, no browser)
- **Scrape Date:** 2026-09-01
- **Input Records:** 21 LinkedIn profiles from data/input/input_channels.csv
- **Output Records:** 21 rows
- **HTTP 200 (public data available):** 5
- **HTTP 999 / blocked:** 16
- **Unique creators:** 21

## Extraction Method

- Direct HTTP requests with browser User-Agent
- OpenGraph meta tags (og:title, og:description) extracted from HTML
- No browser automation — LinkedIn blocks Playwright/headless browsers
- Requests-based approach only retrieves public OG data for some profiles
- 1-second delay between requests

## Known Limitations

- **Major limitation:** LinkedIn aggressively blocks non-browser requests. ~16 of 21 profiles returned HTTP 999 or empty OG data.
- Only 5 profiles returned usable public OG metadata (title, description, region).
- Follower counts are rarely exposed in LinkedIn's public OG tags.
- Email addresses are almost never exposed in public LinkedIn profiles.
- Profiles without OG data are marked as blocked and retain only their pre-existing discovery information.
- For full profile data, LinkedIn Graph API or authenticated browser sessions are required.

## Creator Notes

21 creator notes in `obsidian/Creator Research/Creators/`:
- [[scottieyang]] — @scottieyang — ❌ blocked
- [[elettrafiumi]] — @elettrafiumi — ❌ blocked
- [[jack-masteller-63317022]] — @jack-masteller-63317022 — ❌ blocked
- [[andrewakinyede]] — @andrewakinyede — ❌ blocked
- [[ian-wilmoth]] — Ian Wilmoth — ✅
- [[soukimansoor]] — @soukimansoor — ❌ blocked
- [[characampanella]] — @characampanella — ❌ blocked
- [[mrpixelwizard]] — @mrpixelwizard — ❌ blocked
- [[mausam-puri-747169201]] — @mausam-puri-747169201 — ❌ blocked
- [[junielau]] — @junielau — ❌ blocked
- [[marko-slavnic-3a29209]] — @marko-slavnic-3a29209 — ❌ blocked
- [[digitalwind]] — @digitalwind — ❌ blocked
- [[iansansavera]] — Ian Sansavera — ✅
- [[kunal-khanna-91812420]] — @kunal-khanna-91812420 — ❌ blocked
- [[johnson-sunday-9389912b8]] — @johnson-sunday-9389912b8 — ❌ blocked
- [[elijah-adah]] — Elijah Adah — ✅
- [[patrickmullady]] — Patrick M. — ✅
- [[barnabaslawson]] — @barnabaslawson — ❌ blocked
- [[dave-spector]] — @dave-spector — ❌ blocked
- [[seshagiriraob]] — @seshagiriraob — ❌ blocked
- [[shabhi-haider-65989b75]] — Shabhi Haider — ✅

## AIGC Distribution

- **yes:** profiles identifying as AI filmmakers/creators
- **hybrid:** profiles discussing AI tools or working with AI in creative contexts
- **unsure/unknown:** profiles where public data was insufficient

Most profiles retain discovery-only AIGC verdicts from SearXNG snippets.

## Related

- [[Creator Research System]]
- [[2026-09-01]]
