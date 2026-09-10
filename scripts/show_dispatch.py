import csv
with open('data/output/run_dispatch_output.csv', newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    rows=[row for row in r]
print('Dispatch output rows:', len(rows))
for row in rows:
    print(row.get('ProfileURL'), '|', row.get('Name/Handle'), '|', row.get('Platform'), '|', row.get('OutreachStatus'))
