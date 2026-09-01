---
type: research
platform: Threads
date: 2026-09-01
status: completed
records: 78
---

# Threads AIGC Research — 2026-09-01

## Summary
Scraped 79 Threads profiles from `data/input/input_channels.csv` using the existing Threads scraper (`code/scraper/threads.py`). All 79 profiles were processed and saved to `data/output/threads_scraped_output.csv`.

78 Obsidian creator notes were generated in [[Creators]] (one input row had no valid handle and was skipped from note creation).

## Methodology
- Scraper: Playwright-based `threads.py` (existing, unmodified).
- Input: `data/input/input_channels.csv` (Platform column = "threads" or URL contains threads.net).
- AI classification: local Ollama llama3.2 fallback to rule-based keywords.
- Follower counts extracted from page body text (e.g. "12.5K followers").
- Emails extracted from bio text via regex.

## Key Findings
- Largest Threads accounts in dataset: [[@google]] (3.9M), [[@technology]] (614.2K), [[@evolving.ai]] (528.9K), [[@marketrypro]] (256.7K), [[@instories.app]] (212.1K).
- Mix of official brand/tool accounts ([[@google]], [[@pixverse_official]], [[@buffer]], [[@imagineartofficial]]) and individual AI creators/filmmakers.
- Primary AI tools mentioned across profiles: ChatGPT, Sora, Runway, Kling, Midjourney, Veo, GenAI, Leonardo AI, ElevenLabs, Adobe Firefly, Next-Frame.ai, PixVerse, Jitter Motion, Consistent Character AI, Instories AI, Enhancor.ai, GenFeed, Buffer AI, Google DeepMind, OpenArt, PhotoshAI, GenAI.
- Languages observed: English, Korean, Traditional Chinese, Indonesian, Spanish, Italian, Russian, Thai, Simplified Chinese, Japanese.
- Regions observed: USA, UK, South Korea, Hong Kong, Indonesia, Taiwan, Thailand, India, Italy, Spain, Russia, Japan, France, Germany, Brazil, South Africa, Canada, Australia, Philippines, Norway, Ireland.

## AIGC Verdicts
- Most profiles classified as "hybrid" (mix of AI-assisted and other content) or "yes" (AI-generated content).
- A few profiles classified as "no" (e.g. [[@dago.eldueno]], [[@dominicknero]], [[@sora_film.photography]], [[@moppy.op]]).
- Some profiles have empty/unknown verdicts due to limited profile data.

## Notes
- One profile ([@indraaziz]) had a navigation error during scraping but still produced output via fallback data.
- [[@tag]] has N/A follower count (generic account).
- Emails were exposed for a minority of profiles (e.g. [[@ai.academyhk]], [[@griggen_]], [[@windsjin]], [[@thewillie.35]]).

## Related
- [[Creator Research]]
- [[Threads]]
- [[2026-09-01]]
- `data/output/threads_scraped_output.csv`
