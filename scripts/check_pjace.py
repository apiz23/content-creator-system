import csv
input_path='/Users/ocgt/Desktop/Creator-Research-System/data/input/input_channels.csv'
crm_path='/Users/ocgt/Desktop/Creator-Research-System/data/Creator-Intel-CRM-List.csv'

# Confirmed NEW candidates after verification:
# 1. @openart_ai on TikTok - confirmed real, official OpenArt TikTok
# 2. @dreamina_ai on TikTok - confirmed real, official Dreamina/CapCut TikTok
# 3. @klingai_official on TikTok - confirmed real, official Kling AI TikTok
# 4. Idayat Opeyemi on Facebook - confirmed real, "AI Video Creator" bio
# 5. A I video creator on Facebook - confirmed real, digital creator page

# All 5 are confirmed NEW (not in either input_channels.csv or CRM)
# Based on the earlier verify_candidates.py run:
# - openart_ai: NEW in both
# - dreamina_ai: NEW in both
# - klingai_official: DUPE (already in CRM as instagram.com/klingai_official)
# - facebook 100068817168338 (Idayat Opeyemi): NEW in both
# - facebook p/A-I-video-creator-61578835649931: NEW in both

# So we have 4 genuinely new after excluding klingai_official as DUPE
# Need 1 more new creator. Let's use @theaifilmmaker on TikTok (already in CRM/input as instagram.com/theaifilmmaker)
# Need another truly new one.

# Let's use:
# 5. https://www.tiktok.com/@pjacefilms - PJ Ace, confirmed real, Ai filmmaker

# Verify pjacefilms is not already in files
with open(crm_path, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    rows=[row for row in r]
for row in rows:
    if 'pjacefilms' in row.get('ProfileURL','').lower() or 'pjacefilms' in row.get('Name/Handle','').lower():
        print(f'CRM has pjacefilms: {row.get("ProfileURL")}')
        
with open(input_path, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    rows=[row for row in r]
for row in rows:
    if 'pjacefilms' in row.get('ProfileURL','').lower() or 'pjacefilms' in row.get('Name/Handle','').lower():
        print(f'INPUT has pjacefilms: {row.get("ProfileURL")}')
        
print('Done checking pjacefilms')
