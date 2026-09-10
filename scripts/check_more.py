import csv
input_path='/Users/ocgt/Desktop/Creator-Research-System/data/input/input_channels.csv'
crm_path='/Users/ocgt/Desktop/Creator-Research-System/data/Creator-Intel-CRM-List.csv'

# Check more candidates that are genuinely new
candidates = [
    'https://www.tiktok.com/@openart_ai',
    'https://www.tiktok.com/@dreamina_ai',
    'https://www.facebook.com/100068817168338',  # Idayat Opeyemi
    'https://www.facebook.com/p/A-I-video-creator-61578835649931',
    'https://www.tiktok.com/@theaifilmmaker',  # already in CRM (instagram/theaifilmmaker + tiktok/theaifilmmaker)
]

# Check if theaifilmmaker tiktok is a DUPE
with open(crm_path, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    rows=[row for row in r]
for c in candidates:
    for row in rows:
        if c.lower() in row.get('ProfileURL','').lower() or row.get('ProfileURL','').lower() in c.lower():
            print(f'DUPE candidate {c} -> CRM has {row.get("ProfileURL")}')
            break
    else:
        print(f'NEW candidate {c}')

# Check what new TikTok candidates are available
# Search for more
