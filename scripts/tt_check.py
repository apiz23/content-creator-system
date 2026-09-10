import csv
crm_path='data/Creator-Intel-CRM-List.csv'
with open(crm_path, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    rows=[row for row in r]
tt=[row for row in rows if row.get('Platform','').strip().lower()=='tiktok']
print('TikTok rows in CRM:', len(tt))
for row in tt[:10]:
    print(row.get('ProfileURL'), '|', row.get('Name/Handle'), '|', row.get('Platform'))
