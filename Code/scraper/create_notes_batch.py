import os
from datetime import datetime

today = "2026-09-03"
vault = "/Users/ocgt/Desktop/Creator-Research-System/obsidian/Creator Research/Creators"

notes = [
    {
        "file": "zorilov_ai.md",
        "yaml": f"""---
name: Alexander Zorilov
handle: @zorilov_ai
platform: YouTube
profile_url: https://www.youtube.com/@zorilov_ai
followers: Unknown
email: Not publicly available
category: AI Video / Filmmaking
language: English
region: Unknown
ai_tools: Unknown
status: Discovered
discovered_at: {today}
last_scraped_at: 
last_verified: {today}
---

# Alexander Zorilov (@zorilov_ai)

## Profile

- **Handle:** @zorilov_ai
- **Platform:** YouTube
- **Profile URL:** https://www.youtube.com/@zorilov_ai
- **Follower Count:** Unknown
- **Region:** Unknown
- **Language:** English

## AI / Content

- **AIGC Verdict:** Unsure (discovery-only)
- **Niche:** AI video, filmmaking

## Evidence

- **Source:** YouTube search — AI video creator
- **Source URL:** https://www.youtube.com/@zorilov_ai

## Notes

- Discovered via YouTube search. Not yet scraped.
- [[YouTube]] | [[Daily/{today}]]

## Related

- [[Platforms/YouTube]]
- [[Daily/{today}]]
""",
    },
    {
        "file": "SudarshanTube.md",
        "yaml": f"""---
name: Sudarshan Senthilvel
handle: @SudarshanTube
platform: YouTube
profile_url: https://www.youtube.com/@SudarshanTube
followers: Unknown
email: Not publicly available
category: AI Filmmaking / Music / Education
language: English
region: India / US
ai_tools: Unknown
status: Discovered
discovered_at: {today}
last_scraped_at: 
last_verified: {today}
---

# Sudarshan Senthilvel (@SudarshanTube)

## Profile

- **Handle:** @SudarshanTube
- **Platform:** YouTube
- **Profile URL:** https://www.youtube.com/@SudarshanTube
- **Follower Count:** Unknown (Top 1% YPP channel)
- **Region:** India / US
- **Language:** English

## AI / Content

- **AIGC Verdict:** Unsure (discovery-only)
- **Niche:** AI filmmaking, music composition, XR/VR, education
- **Bio:** Hollywood Grade YouTube Channel. Google DeepMind Trusted Tester. Stanford Arts grad, Berklee-certified musician. 24 subjects covered.

## Evidence

- **Source:** LinkedIn search — Sudarshan Senthilvel
- **Source URL:** https://www.linkedin.com/in/sudarshanxr

## Notes

- Discovered via search. Not yet scraped.
- Google DeepMind Trusted Tester — significant credential.
- Multi-disciplinary: AI filmmaking, music, cooking, finance, XR.
- [[YouTube]] | [[Daily/{today}]]

## Related

- [[Platforms/YouTube]]
- [[Daily/{today}]]
""",
    },
    {
        "file": "dorbrothers.md",
        "yaml": f"""---
name: The Dor Brothers (Dan & Phil Dor)
handle: @dorbrothers
platform: YouTube
profile_url: https://www.youtube.com/@dorbrothers
followers: Unknown
email: Not publicly available
category: AI Filmmaking
language: English
region: London, UK / Lisbon, Portugal
ai_tools: Veo, Hailuo AI, Midjourney, Runway
status: Discovered
discovered_at: {today}
last_scraped_at: 
last_verified: {today}
---

# The Dor Brothers (@dorbrothers)

## Profile

- **Handle:** @dorbrothers
- **Platform:** YouTube
- **Profile URL:** https://www.youtube.com/@dorbrothers
- **Follower Count:** Unknown
- **Region:** London, UK / Lisbon, Portugal
- **Language:** English

## AI / Content

- **AIGC Verdict:** Unsure (discovery-only)
- **Niche:** AI filmmaking, AI animation, satire
- **Tools:** Google Veo 3.1, Hailuo AI, Midjourney, Runway, ChatGPT (prompt refinement)

## Evidence

- **Source:** Deadline interview — The Dor Brothers Target Hollywood
- **Source URL:** https://deadline.com/2025/12/the-dor-brothers-interview-hollywood-joe-rogan-snoop-dogg-1236634355

## Notes

- Discovered via search. Not yet scraped.
- Early Midjourney, Stable Diffusion, Runway users (first 100).
- Founded AI production company "The Dor".
- Joe Rogan praised their AI videos. Snoop Dogg among judges for The Dor Awards.
- Scripted sequel to Idiocracy in development.
- [[YouTube]] | [[Daily/{today}]]

## Related

- [[Platforms/YouTube]]
- [[Daily/{today}]]
""",
    },
    {
        "file": "dayan-ahmed.md",
        "yaml": f"""---
name: Dayan Ahmed
handle: dayan-ahmed
platform: LinkedIn
profile_url: https://www.linkedin.com/in/dayaan-ahmed-6681712b4
followers: Not publicly available
email: Not publicly available
category: Generative AI Filmmaking
language: English
region: Unknown
ai_tools: Unknown
status: Discovered
discovered_at: {today}
last_scraped_at: 
last_verified: {today}
---

# Dayan Ahmed

## Profile

- **Handle:** dayan-ahmed
- **Platform:** LinkedIn
- **Profile URL:** https://www.linkedin.com/in/dayaan-ahmed-6681712b4
- **Follower Count:** Not publicly available
- **Region:** Unknown
- **Language:** English

## AI / Content

- **AIGC Verdict:** Unsure (discovery-only)
- **Niche:** Generative AI filmmaking, cinematic visuals
- **Bio:** Generative AI Filmmaker specializing in cinematic visuals, AI-driven storytelling, immersive digital narratives. Chroma Awards 2025.

## Evidence

- **Source:** LinkedIn search
- **Source URL:** https://www.linkedin.com/in/dayaan-ahmed-6681712b4

## Notes

- Discovered via LinkedIn search. Not yet scraped.
- Chroma Awards 2025 — notable recognition.
- CPP at multiple AI platforms: invideo.io, openart_ai, pixverse, klingai, dreamina_ai, thankyouai.hq.
- [[LinkedIn]] | [[Daily/{today}]]

## Related

- [[Platforms/LinkedIn]]
- [[Daily/{today}]]
""",
    },
    {
        "file": "yousef-k.md",
        "yaml": f"""---
name: Yousef K.
handle: yousef-k
platform: LinkedIn
profile_url: https://www.linkedin.com/in/yousef-k-956b996a
followers: Not publicly available
email: Not publicly available
category: AI Filmmaking
language: English
region: Unknown
ai_tools: Seedance, GPT Image 2, Luma AI, Dreamina
status: Discovered
discovered_at: {today}
last_scraped_at: 
last_verified: {today}
---

# Yousef K.

## Profile

- **Handle:** yousef-k
- **Platform:** LinkedIn
- **Profile URL:** https://www.linkedin.com/in/yousef-k-956b996a
- **Follower Count:** Not publicly available
- **Region:** Unknown
- **Language:** English

## AI / Content

- **AIGC Verdict:** Unsure (discovery-only)
- **Niche:** AI filmmaking, cinematic concept films, proof-of-concept trailers
- **Bio:** Multi-award-winning independent AI filmmaker. Dreamina Creative Partner. Creates cinematic concept films and proof-of-concept trailers.

## Evidence

- **Source:** LinkedIn search
- **Source URL:** https://www.linkedin.com/in/yousef-k-956b996a

## Notes

- Discovered via LinkedIn search. Not yet scraped.
- Multi-award-winning — notable achievement in AI filmmaking.
- Dreamina Creative Partner.
- Working on horror/sci-fi AI short film "UNSUMMONED" for festival submissions.
- Uses Seedance 2.5, GPT Image 2, Luma AI, Dreamina.
- [[LinkedIn]] | [[Daily/{today}]]

## Related

- [[Platforms/LinkedIn]]
- [[Daily/{today}]]
""",
    },
    {
        "file": "max-sawicki.md",
        "yaml": f"""---
name: Max Sawicki
handle: max-sawicki
platform: LinkedIn
profile_url: https://www.linkedin.com/in/max-sawicki-020ba9322
followers: Not publicly available
email: Not publicly available
category: AI Video / Creative Technology
language: English
region: Unknown
ai_tools: ComfyUI, Blender, Unreal Engine
status: Discovered
discovered_at: {today}
last_scraped_at: 
last_verified: {today}
---

# Max Sawicki

## Profile

- **Handle:** max-sawicki
- **Platform:** LinkedIn
- **Profile URL:** https://www.linkedin.com/in/max-sawicki-020ba9322
- **Follower Count:** Not publicly available
- **Region:** Unknown
- **Language:** English

## AI / Content

- **AIGC Verdict:** Unsure (discovery-only)
- **Niche:** AI video, creative technology, ComfyUI workflows
- **Bio:** Creative Technologist | AI & Video Specialist. 440K+ YouTube subscribers, 45M+ views. Adobe MAX Insider/Ambassador. Collaborated with Google VEO team.

## Evidence

- **Source:** LinkedIn search
- **Source URL:** https://www.linkedin.com/in/max-sawicki-020ba9322

## Notes

- Discovered via LinkedIn search. Not yet scraped.
- 440K+ YouTube subscribers — significant audience.
- Adobe MAX Insider, collaborated with Google VEO team.
- ComfyUI, Blender, Unreal Engine expert.
- YouTube channel teaches advanced workflows in Adobe Creative Suite, ComfyUI.
- [[LinkedIn]] | [[Daily/{today}]]

## Related

- [[Platforms/LinkedIn]]
- [[Daily/{today}]]
""",
    },
    {
        "file": "nell-lundy.md",
        "yaml": f"""---
name: Nell Lundy
handle: nell-lundy
platform: LinkedIn
profile_url: https://www.linkedin.com/in/nell-lundy-1178b82
followers: Not publicly available
email: Not publicly available
category: Generative AI / Immersive Media
language: English
region: Unknown
ai_tools: Unknown
status: Discovered
discovered_at: {today}
last_scraped_at: 
last_verified: {today}
---

# Nell Lundy

## Profile

- **Handle:** nell-lundy
- **Platform:** LinkedIn
- **Profile URL:** https://www.linkedin.com/in/nell-lundy-1178b82
- **Follower Count:** Not publicly available
- **Region:** Unknown
- **Language:** English

## AI / Content

- **AIGC Verdict:** Unsure (discovery-only)
- **Niche:** Generative AI, immersive media, experiential storytelling
- **Bio:** Creative director and producer. Works with experiential storytelling, production systems, live audiences, and enterprise clients.

## Evidence

- **Source:** LinkedIn search
- **Source URL:** https://www.linkedin.com/in/nell-lundy-1178b82

## Notes

- Discovered via LinkedIn search. Not yet scraped.
- Focus on generative AI and immersive media for enterprise clients.
- [[LinkedIn]] | [[Daily/{today}]]

## Related

- [[Platforms/LinkedIn]]
- [[Daily/{today}]]
""",
    },
    {
        "file": "matthewszewczyk1.md",
        "yaml": f"""---
name: Matthew Szewczyk
handle: matthewszewczyk1
platform: LinkedIn
profile_url: https://www.linkedin.com/in/matthewszewczyk1
followers: Not publicly available
email: Not publicly available
category: AI Video / Filmmaking
language: English
region: Unknown
ai_tools: Unknown
status: Discovered
discovered_at: {today}
last_scraped_at: 
last_verified: {today}
---

# Matthew Szewczyk

## Profile

- **Handle:** matthewszewczyk1
- **Platform:** LinkedIn
- **Profile URL:** https://www.linkedin.com/in/matthewszewczyk1
- **Follower Count:** Not publicly available
- **Region:** Unknown
- **Language:** English

## AI / Content

- **AIGC Verdict:** Unsure (discovery-only)
- **Niche:** AI video, filmmaking
- **Bio:** Created viral AI video project "Living in America". Uses directorial skills from film school to string together AI-generated content.

## Evidence

- **Source:** LinkedIn search
- **Source URL:** https://www.linkedin.com/in/matthewszewczyk1

## Notes

- Discovered via LinkedIn search. Not yet scraped.
- Viral AI video project "Living in America" — notable for demonstrating AI filmmaking evolution.
- Film school background applied to AI content creation.
- [[LinkedIn]] | [[Daily/{today}]]

## Related

- [[Platforms/LinkedIn]]
- [[Daily/{today}]]
""",
    },
    {
        "file": "kelly-boesch.md",
        "yaml": f"""---
name: Kelly Boesch
handle: kelly-boesch
platform: LinkedIn
profile_url: https://www.linkedin.com/in/kelly-boesch
followers: Not publicly available
email: Not publicly available
category: AI Art / AI Tools
language: English
region: Unknown
ai_tools: Unknown
status: Discovered
discovered_at: {today}
last_scraped_at: 
last_verified: {today}
---

# Kelly Boesch

## Profile

- **Handle:** kelly-boesch
- **Platform:** LinkedIn
- **Profile URL:** https://www.linkedin.com/in/kelly-boesch
- **Follower Count:** Not publicly available
- **Region:** Unknown
- **Language:** English

## AI / Content

- **AIGC Verdict:** Unsure (discovery-only)
- **Niche:** AI art, AI tools, creative visual work
- **Bio:** AI Tools Artist Spotlight (ProVideo Coalition interview). One of AI creative visual pioneers.

## Evidence

- **Source:** ProVideo Coalition — AI Tools Artist Spotlight: Kelly Boesch
- **Source URL:** https://www.provideocoalition.com/ai-tools-artist-spotlight-kelly-boesch/

## Notes

- Discovered via search. Not yet scraped.
- Featured in ProVideo Coalition's AI Tools Artist Spotlight.
- Recognized as one of AI's creative visual pioneers.
- [[LinkedIn]] | [[Daily/{today}]]

## Related

- [[Platforms/LinkedIn]]
- [[Daily/{today}]]
""",
    },
    {
        "file": "KavanTheKid.md",
        "yaml": f"""---
name: Kavan Cardoza (Kavan the Kid)
handle: @KavanTheKid
platform: YouTube
profile_url: https://www.youtube.com/@KavanTheKid
followers: Unknown
email: Not publicly available
category: AI Filmmaking / IP Creation
language: English
region: US
ai_tools: Veo, Seedance 2.0
status: Discovered
discovered_at: {today}
last_scraped_at: 
last_verified: {today}
---

# Kavan Cardoza (@KavanTheKid)

## Profile

- **Handle:** @KavanTheKid
- **Platform:** YouTube
- **Profile URL:** https://www.youtube.com/@KavanTheKid
- **Follower Count:** Unknown
- **Region:** US
- **Language:** English

## AI / Content

- **AIGC Verdict:** Unsure (discovery-only)
- **Niche:** AI filmmaking, IP creation, animated series
- **Bio:** Creates "The Chronicles of Bone" — dark fantasy AI animated series. Writes, generates, edits, scores, and sound designs alone. ~1 episode per month.

## Evidence

- **Source:** Yahoo Finance / Kavan the Kid Builds AI Film Characters He Owns
- **Source URL:** https://finance.yahoo.com/technology/ai/articles/kavan-kid-builds-ai-film-193003894.html

## Notes

- Discovered via search. Not yet scraped.
- Copyright-registered scripts and character designs — unusual for AI creator.
- Trademarked series title.
- 11.5 min episodes take 14-16 days using Veo/Seedance 2.0.
- Phantom X cofounder Sav assists with VFX cleanup.
- Batman fan film went viral (1M+ views) before being taken down by Warner Bros. claim.
- [[YouTube]] | [[Daily/{today}]]

## Related

- [[Platforms/YouTube]]
- [[Daily/{today}]]
""",
    },
]

written = 0
for note in notes:
    path = os.path.join(vault, note["file"])
    with open(path, "w") as f:
        f.write(note["yaml"])
    written += 1
    print(f"Written: {note['file']}")

print(f"\nTotal: {written} creator notes created")
