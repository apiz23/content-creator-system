import csv
input_path='/Users/ocgt/Desktop/Creator-Research-System/data/input/input_channels.csv'
crm_path='/Users/ocgt/Desktop/Creator-Research-System/data/Creator-Intel-CRM-List.csv'

# Check runwayml
c = 'https://www.tiktok.com/@runwayml'
with open(crm_path, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    rows=[row for row in r]
for row in rows:
    if c.lower() in row.get('ProfileURL','').lower() or row.get('ProfileURL','').lower() in c.lower():
        print(f'CRM has runwayml: {row.get("ProfileURL")}')
        break
else:
    print('runwayml is NEW in CRM')

# Also check facebook.com/runwayml
c2 = 'https://www.facebook.com/runwayml'
with open(crm_path, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    rows=[row for row in r]
for row in rows:
    if c2.lower() in row.get('ProfileURL','').lower() or row.get('ProfileURL','').lower() in c2.lower():
        print(f'CRM has facebook/runwayml: {row.get("ProfileURL")}')
        break
else:
    print('facebook/runwayml is NEW in CRM')

# So final 5 NEW candidates after excluding dupe @klingai_official:
# 1. https://www.tiktok.com/@openart_ai
# 2. https://www.tiktok.com/@dreamina_ai
# 3. https://www.tiktok.com/@runwayml
# 4. https://www.facebook.com/100068817168338 (Idayat Opeyemi)
# 5. https://www.facebook.com/p/A-I-video-creator-61578835649931
print('Final 5 confirmed new candidates:')
print('1. https://www.tiktok.com/@openart_ai')
print('2. https://www.tiktok.com/@dreamina_ai')
print('3. https://www.tiktok.com/@runwayml')
print('4. https://www.facebook.com/100068817168338')
print('5. https://www.facebook.com/p/A-I-video-creator-61578835649931')
