import csv
with open('data/Creator-Intel-CRM-List.csv', newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    rows=[row for row in r]
print('CRM row count after scraping:', len(rows))
for row in rows[-5:]:
    print(row.get('ProfileURL'), '|', row.get('Name/Handle'), '|', row.get('Platform'))
