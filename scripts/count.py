import csv
with open('data/Creator-Intel-CRM-List.csv', newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    rows=[row for row in r]
print('CRM row count:', len(rows))
with open('data/input/input_channels.csv', newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    rows=[row for row in r]
print('Input channel row count:', len(rows))
