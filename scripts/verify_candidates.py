import csv
input_path='/Users/ocgt/Desktop/Creator-Research-System/data/input/input_channels.csv'
crm_path='/Users/ocgt/Desktop/Creator-Research-System/data/Creator-Intel-CRM-List.csv'

candidates = [
    'https://www.tiktok.com/@openart_ai',
    'https://www.tiktok.com/@dreamina_ai',
    'https://www.tiktok.com/@klingai_official',
    'https://www.facebook.com/100068817168338',
    'https://www.facebook.com/p/A-I-video-creator-61578835649931',
]

for label, path in [('INPUT', input_path), ('CRM', crm_path)]:
    print('===', label, '===')
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        rows=[row for row in r]
    for c in candidates:
        found=False
        for row in rows:
            if row.get('ProfileURL','').strip().lower()==c.lower() or row.get('Name/Handle','').strip().lower() in c.lower() or c.lower() in row.get('ProfileURL','').lower() or c.lower() in row.get('Name/Handle','').lower():
                found=True
                print(f'  DUPE: {c} -> match in row with URL={row.get("ProfileURL")}')
                break
        if not found:
            print(f'  NEW: {c}')
