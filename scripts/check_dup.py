import csv, re
input_path='/Users/ocgt/Desktop/Creator-Research-System/data/input/input_channels.csv'
crm_path='/Users/ocgt/Desktop/Creator-Research-System/data/Creator-Intel-CRM-List.csv'
terms=['theaifilmmaker','pjacefilms','facebook.com','tiktok.com']
for name, path in [('input', input_path), ('crm', crm_path)]:
    print('===', name, '===')
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        rows=[row for row in r]
    for term in terms:
        matches=[row.get('ProfileURL','') for row in rows if term.lower() in row.get('ProfileURL','').lower() or term.lower() in row.get('Name/Handle','').lower()]
        print(term, len(matches), matches[:5])
    print('rows', len(rows))
