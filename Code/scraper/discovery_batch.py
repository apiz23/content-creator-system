import csv
from datetime import datetime

now_iso = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

new_creators = [
    # YouTube
    {
        'ProfileURL': 'https://www.youtube.com/@zorilov_ai',
        'Name/Handle': '@zorilov_ai',
        'Platform': 'YouTube',
        'FollowerCount': '',
        'Email': 'not exposed',
        'Tags': 'AIGC,YouTube,AI video,filmmaking',
        'OutreachStatus': 'New',
        'LastScrapedAt': '',
        'Region': 'Unknown',
        'Language': 'en',
        'PrimaryAITool': 'Unknown',
        'SampleContentURL': 'https://www.youtube.com/@zorilov_ai',
        'AIGCVerdict': 'unsure',
        'DiscoveredAt': now_iso,
        'Source': 'web_search: AI video YouTube creator search 2025',
        'Notes': 'Alexander Zorilov. AI video creator on YouTube.',
        'FeedURL': 'https://www.youtube.com/@zorilov_ai',
        'ContactSourceURL': '',
        'EvidenceJSON': '{"discovery": {"source": "web_search", "url": "https://www.youtube.com/@zorilov_ai", "title": "Alexander Zorilov - YouTube"}}',
    },
    {
        'ProfileURL': 'https://www.youtube.com/@SudarshanTube',
        'Name/Handle': '@SudarshanTube',
        'Platform': 'YouTube',
        'FollowerCount': '',
        'Email': 'not exposed',
        'Tags': 'AIGC,YouTube,AI filmmaking,music',
        'OutreachStatus': 'New',
        'LastScrapedAt': '',
        'Region': 'India',
        'Language': 'en',
        'PrimaryAITool': 'Unknown',
        'SampleContentURL': 'https://www.youtube.com/@SudarshanTube',
        'AIGCVerdict': 'unsure',
        'DiscoveredAt': now_iso,
        'Source': 'web_search: AI video YouTube creator search 2025',
        'Notes': 'Sudarshan Senthilvel. AI filmmaker, Google DeepMind Trusted Tester. Top 1% YPP channel. Stanford Arts grad, Berklee-certified musician.',
        'FeedURL': 'https://www.youtube.com/@SudarshanTube',
        'ContactSourceURL': '',
        'EvidenceJSON': '{"discovery": {"source": "web_search", "url": "https://www.youtube.com/@SudarshanTube", "title": "SudarshanTube - AI Filmmaker"}}',
    },
    {
        'ProfileURL': 'https://www.youtube.com/@dorbrothers',
        'Name/Handle': '@dorbrothers',
        'Platform': 'YouTube',
        'FollowerCount': '',
        'Email': 'not exposed',
        'Tags': 'AIGC,YouTube,AI filmmaking,Veo',
        'OutreachStatus': 'New',
        'LastScrapedAt': '',
        'Region': 'London, UK',
        'Language': 'en',
        'PrimaryAITool': 'Veo',
        'SampleContentURL': 'https://www.youtube.com/@dorbrothers',
        'AIGCVerdict': 'unsure',
        'DiscoveredAt': now_iso,
        'Source': 'web_search: AI video YouTube creator search 2025',
        'Notes': 'The Dor Brothers (Dan & Phil Dor). Lisbon-based AI filmmaking duo. Early Midjourney/Runway users. Use Veo 3.1 and Hailuo AI. Founded The Dor AI production company.',
        'FeedURL': 'https://www.youtube.com/@dorbrothers',
        'ContactSourceURL': '',
        'EvidenceJSON': '{"discovery": {"source": "web_search", "url": "https://www.youtube.com/@dorbrothers", "title": "The Dor Brothers - AI Filmmakers"}}',
    },
    # LinkedIn
    {
        'ProfileURL': 'https://www.linkedin.com/in/dayaan-ahmed-6681712b4',
        'Name/Handle': 'Dayan Ahmed',
        'Platform': 'LinkedIn',
        'FollowerCount': 'not exposed',
        'Email': 'not exposed',
        'Tags': 'AIGC,LinkedIn,AI filmmaking,generative video',
        'OutreachStatus': 'New',
        'LastScrapedAt': '',
        'Region': 'Unknown',
        'Language': 'en',
        'PrimaryAITool': 'Unknown',
        'SampleContentURL': 'https://www.linkedin.com/in/dayaan-ahmed-6681712b4',
        'AIGCVerdict': 'unsure',
        'DiscoveredAt': now_iso,
        'Source': 'web_search: LinkedIn AI filmmaker search 2025',
        'Notes': 'Generative AI Filmmaker. Chroma Awards 2025. CPP at invideo.io, openart_ai, pixverse, klingai, dreamina_ai, thankyouai.hq.',
        'FeedURL': 'https://www.linkedin.com/in/dayaan-ahmed-6681712b4',
        'ContactSourceURL': '',
        'EvidenceJSON': '{"discovery": {"source": "LinkedIn search", "url": "https://www.linkedin.com/in/dayaan-ahmed-6681712b4", "title": "Dayan Ahmed - Generative AI Filmmaker"}}',
    },
    {
        'ProfileURL': 'https://www.linkedin.com/in/yousef-k-956b996a',
        'Name/Handle': 'Yousef K.',
        'Platform': 'LinkedIn',
        'FollowerCount': 'not exposed',
        'Email': 'not exposed',
        'Tags': 'AIGC,LinkedIn,AI filmmaking,Dreamina',
        'OutreachStatus': 'New',
        'LastScrapedAt': '',
        'Region': 'Unknown',
        'Language': 'en',
        'PrimaryAITool': 'Seedance',
        'SampleContentURL': 'https://www.linkedin.com/in/yousef-k-956b996a',
        'AIGCVerdict': 'unsure',
        'DiscoveredAt': now_iso,
        'Source': 'web_search: LinkedIn AI filmmaker search 2025',
        'Notes': 'Multi-award-winning independent AI filmmaker. Dreamina Creative Partner. Creates cinematic concept films and proof-of-concept trailers with Seedance 2.5, GPT Image 2, Luma AI.',
        'FeedURL': 'https://www.linkedin.com/in/yousef-k-956b996a',
        'ContactSourceURL': '',
        'EvidenceJSON': '{"discovery": {"source": "LinkedIn search", "url": "https://www.linkedin.com/in/yousef-k-956b996a", "title": "Yousef K. - AI Filmmaker"}}',
    },
    {
        'ProfileURL': 'https://www.linkedin.com/in/max-sawicki-020ba9322',
        'Name/Handle': 'Max Sawicki',
        'Platform': 'LinkedIn',
        'FollowerCount': 'not exposed',
        'Email': 'not exposed',
        'Tags': 'AIGC,LinkedIn,AI video,ComfyUI,creative tech',
        'OutreachStatus': 'New',
        'LastScrapedAt': '',
        'Region': 'Unknown',
        'Language': 'en',
        'PrimaryAITool': 'ComfyUI',
        'SampleContentURL': 'https://www.linkedin.com/in/max-sawicki-020ba9322',
        'AIGCVerdict': 'unsure',
        'DiscoveredAt': now_iso,
        'Source': 'web_search: LinkedIn AI video creator search 2025',
        'Notes': 'Creative Technologist | AI & Video Specialist. 440K+ YouTube subscribers, 45M+ views. ComfyUI, Blender, Unreal Engine expert. Adobe MAX Insider. Collaborated with Google VEO team.',
        'FeedURL': 'https://www.linkedin.com/in/max-sawicki-020ba9322',
        'ContactSourceURL': '',
        'EvidenceJSON': '{"discovery": {"source": "LinkedIn search", "url": "https://www.linkedin.com/in/max-sawicki-020ba9322", "title": "Max Sawicki - Creative Technologist"}}',
    },
    {
        'ProfileURL': 'https://www.linkedin.com/in/nell-lundy-1178b82',
        'Name/Handle': 'Nell Lundy',
        'Platform': 'LinkedIn',
        'FollowerCount': 'not exposed',
        'Email': 'not exposed',
        'Tags': 'AIGC,LinkedIn,generative AI,immersive media',
        'OutreachStatus': 'New',
        'LastScrapedAt': '',
        'Region': 'Unknown',
        'Language': 'en',
        'PrimaryAITool': 'Unknown',
        'SampleContentURL': 'https://www.linkedin.com/in/nell-lundy-1178b82',
        'AIGCVerdict': 'unsure',
        'DiscoveredAt': now_iso,
        'Source': 'web_search: LinkedIn generative AI creator search 2025',
        'Notes': 'Creative director and producer. Works with experiential storytelling, production systems, live audiences, and enterprise clients. Generative AI and immersive media focus.',
        'FeedURL': 'https://www.linkedin.com/in/nell-lundy-1178b82',
        'ContactSourceURL': '',
        'EvidenceJSON': '{"discovery": {"source": "LinkedIn search", "url": "https://www.linkedin.com/in/nell-lundy-1178b82", "title": "Nell Lundy - Generative AI"}}',
    },
    {
        'ProfileURL': 'https://www.linkedin.com/in/matthewszewczyk1',
        'Name/Handle': 'Matthew Szewczyk',
        'Platform': 'LinkedIn',
        'FollowerCount': 'not exposed',
        'Email': 'not exposed',
        'Tags': 'AIGC,LinkedIn,AI video,filmmaking',
        'OutreachStatus': 'New',
        'LastScrapedAt': '',
        'Region': 'Unknown',
        'Language': 'en',
        'PrimaryAITool': 'Unknown',
        'SampleContentURL': 'https://www.linkedin.com/in/matthewszewczyk1',
        'AIGCVerdict': 'unsure',
        'DiscoveredAt': now_iso,
        'Source': 'web_search: LinkedIn AI video creator search 2025',
        'Notes': 'Created viral AI video project "Living in America". Uses directorial skills from film school to string together AI-generated content.',
        'FeedURL': 'https://www.linkedin.com/in/matthewszewczyk1',
        'ContactSourceURL': '',
        'EvidenceJSON': '{"discovery": {"source": "LinkedIn search", "url": "https://www.linkedin.com/in/matthewszewczyk1", "title": "Matthew Szewczyk - AI Video"}}',
    },
    {
        'ProfileURL': 'https://www.linkedin.com/in/kelly-boesch',
        'Name/Handle': 'Kelly Boesch',
        'Platform': 'LinkedIn',
        'FollowerCount': 'not exposed',
        'Email': 'not exposed',
        'Tags': 'AIGC,LinkedIn,AI art,AI tools',
        'OutreachStatus': 'New',
        'LastScrapedAt': '',
        'Region': 'Unknown',
        'Language': 'en',
        'PrimaryAITool': 'Unknown',
        'SampleContentURL': 'https://www.linkedin.com/in/kelly-boesch',
        'AIGCVerdict': 'unsure',
        'DiscoveredAt': now_iso,
        'Source': 'web_search: LinkedIn AI artist search 2025',
        'Notes': 'AI Tools Artist Spotlight (ProVideo Coalition interview). One of AI creative visual pioneers.',
        'FeedURL': 'https://www.linkedin.com/in/kelly-boesch',
        'ContactSourceURL': '',
        'EvidenceJSON': '{"discovery": {"source": "web_search", "url": "https://www.linkedin.com/in/kelly-boesch", "title": "Kelly Boesch - AI Artist"}}',
    },
    {
        'ProfileURL': 'https://www.youtube.com/@KavanTheKid',
        'Name/Handle': '@KavanTheKid',
        'Platform': 'YouTube',
        'FollowerCount': '',
        'Email': 'not exposed',
        'Tags': 'AIGC,YouTube,AI filmmaking,IP',
        'OutreachStatus': 'New',
        'LastScrapedAt': '',
        'Region': 'US',
        'Language': 'en',
        'PrimaryAITool': 'Veo',
        'SampleContentURL': 'https://www.youtube.com/@KavanTheKid',
        'AIGCVerdict': 'unsure',
        'DiscoveredAt': now_iso,
        'Source': 'web_search: AI video YouTube creator search 2025',
        'Notes': 'Kavan Cardoza (Kavan the Kid). Creates "The Chronicles of Bone" AI animated series.Copyright-registered scripts and character designs. Uses Veo and Seedance 2.0. 11.5 min episodes take 14-16 days.',
        'FeedURL': 'https://www.youtube.com/@KavanTheKid',
        'ContactSourceURL': '',
        'EvidenceJSON': '{"discovery": {"source": "web_search", "url": "https://www.youtube.com/@KavanTheKid", "title": "Kavan the Kid - AI Filmmaker"}}',
    },
]

# Append to input CSV
input_path = 'data/input/input_channels.csv'
with open(input_path, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    existing_rows = list(reader)
    fieldnames = reader.fieldnames

print(f"Existing input rows: {len(existing_rows)}")

url_set = {r['ProfileURL'].strip().lower() for r in existing_rows}
duplicates = [c for c in new_creators if c['ProfileURL'].strip().lower() in url_set]
truly_new = [c for c in new_creators if c['ProfileURL'].strip().lower() not in url_set]

if duplicates:
    for d in duplicates:
        print(f"DUPLICATE in input: {d['ProfileURL']}")

all_rows = existing_rows + truly_new

with open(input_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)

print(f"Input CSV: {len(all_rows)} rows ({len(truly_new)} new added, {len(duplicates)} duplicates skipped)")

# Append to CRM
crm_path = 'data/Creator-Intel-CRM-List.csv'
with open(crm_path, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    crm_rows = list(reader)
    crm_fields = reader.fieldnames

crm_urls = {r['ProfileURL'].strip().lower() for r in crm_rows}
crm_duplicates = [c for c in truly_new if c['ProfileURL'].strip().lower() in crm_urls]
crm_new = [c for c in truly_new if c['ProfileURL'].strip().lower() not in crm_urls]

print(f"CRM existing: {len(crm_rows)}")
print(f"CRM duplicates (already in CRM): {len(crm_duplicates)}")
for d in crm_duplicates:
    print(f"  Already in CRM: {d['ProfileURL']}")
print(f"CRM new: {len(crm_new)}")

if crm_new:
    all_crm = crm_rows + crm_new
    with open(crm_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=crm_fields)
        writer.writeheader()
        writer.writerows(all_crm)
    print(f"CRM written: {len(all_crm)} rows")

print(f"\nSummary:")
print(f"  Input CSV: {len(all_rows)} total")
print(f"  CRM: {len(crm_rows) + len(crm_new)} total")
print(f"  New creators added to input: {len(truly_new)}")
print(f"  New creators added to CRM: {len(crm_new)}")
print(f"  Duplicates skipped (input): {len(duplicates)}")
print(f"  Already in CRM: {len(crm_duplicates)}")
