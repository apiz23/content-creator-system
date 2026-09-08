import pandas as pd
import json
import os
import re

scrape_path = 'data/output/instagram_scraped_output.csv'
crm_path = 'data/Creator-Intel-CRM-List.csv'
vault = 'obsidian/Creator Research/Creators'
today = '2026-09-03'

scrape_df = pd.read_csv(scrape_path, dtype=str).fillna('')
print(f"Scrape output: {len(scrape_df)} rows")

crm = pd.read_csv(crm_path, dtype=str).fillna('')
crm_urls = set(crm['ProfileURL'].str.lower())
print(f"CRM: {len(crm)} rows")

updated_crm = 0
new_crm = 0
notes_created = 0
notes_updated = 0

for idx, row in scrape_df.iterrows():
    url = str(row['ProfileURL']).strip()
    handle = str(row['Name/Handle']).strip()
    followers = str(row['FollowerCount']).strip()
    email = str(row['Email']).strip()
    tags = str(row['Tags']).strip()
    language = str(row['Language']).strip()
    primary_tool = str(row['PrimaryAITool']).strip()
    aigc = str(row['AIGCVerdict']).strip()
    notes = str(row['Notes']).strip()
    sample_url = str(row['SampleContentURL']).strip()
    evidence_json = str(row['EvidenceJSON']).strip()
    last_scraped = str(row['LastScrapedAt']).strip()
    region = str(row['Region']).strip()
    feed_url = str(row['FeedURL']).strip()
    contact_url = str(row['ContactSourceURL']).strip()
    source = str(row['Source']).strip()
    discovered = str(row['DiscoveredAt']).strip()
    
    if not url or url == 'nan':
        continue
    
    url_lower = url.lower()
    
    if url_lower in crm_urls:
        mask = crm['ProfileURL'].str.lower() == url_lower
        crm.loc[mask, 'FollowerCount'] = followers
        crm.loc[mask, 'Email'] = email if email and email != 'nan' else crm.loc[mask, 'Email']
        crm.loc[mask, 'Tags'] = tags
        crm.loc[mask, 'Language'] = language
        crm.loc[mask, 'PrimaryAITool'] = primary_tool if primary_tool and primary_tool != 'nan' else crm.loc[mask, 'PrimaryAITool']
        crm.loc[mask, 'AIGCVerdict'] = aigc
        crm.loc[mask, 'LastScrapedAt'] = last_scraped
        crm.loc[mask, 'Region'] = region
        crm.loc[mask, 'SampleContentURL'] = sample_url if sample_url and sample_url != 'nan' else crm.loc[mask, 'SampleContentURL']
        crm.loc[mask, 'Notes'] = notes
        crm.loc[mask, 'FeedURL'] = feed_url
        crm.loc[mask, 'ContactSourceURL'] = contact_url
        crm.loc[mask, 'EvidenceJSON'] = evidence_json
        updated_crm += 1
        print(f"  UPDATED CRM: {handle}")
    else:
        new_row = {
            'ProfileURL': url, 'Name/Handle': handle, 'Platform': 'Instagram',
            'FollowerCount': followers, 'Email': email, 'Tags': tags,
            'OutreachStatus': 'New', 'LastScrapedAt': last_scraped,
            'Region': region, 'Language': language,
            'PrimaryAITool': primary_tool if primary_tool and primary_tool != 'nan' else '',
            'SampleContentURL': sample_url, 'AIGCVerdict': aigc,
            'DiscoveredAt': discovered, 'Source': source, 'Notes': notes,
            'FeedURL': feed_url, 'ContactSourceURL': contact_url, 'EvidenceJSON': evidence_json,
        }
        crm = pd.concat([crm, pd.DataFrame([new_row])], ignore_index=True)
        new_crm += 1
        print(f"  NEW CRM: {handle}")
    
    handle_clean = handle.lstrip('@').replace('.', '_')
    note_path = os.path.join(vault, f"{handle_clean}.md")
    note_exists = os.path.exists(note_path)
    
    email_final = email
    if not email_final or email_final in ('nan', 'not exposed', ''):
        try:
            ev = json.loads(evidence_json) if evidence_json and evidence_json != 'nan' else {}
            bp = ev.get('bio_preview', '') or ev.get('og_description', '')
            m = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', str(bp))
            if m:
                email_final = m.group(0)
        except:
            pass
    
    name = handle.lstrip('@') if handle.startswith('@') else handle
    
    bio_text = ''
    try:
        ev = json.loads(evidence_json) if evidence_json and evidence_json != 'nan' else {}
        bio_text = ev.get('bio_preview', '') or ev.get('og_description', '')
    except:
        pass
    
    note_content = f"""---
name: {name}
handle: {handle}
platform: Instagram
profile_url: {url}
followers: {followers}
email: {email_final if email_final and email_final not in ('nan', 'not exposed', '') else 'Not publicly available'}
category: {tags}
language: {language}
region: {region}
ai_tools: {primary_tool if primary_tool and primary_tool not in ('nan', '') else 'Unknown'}
status: Scraped
discovered_at: {discovered}
last_scraped_at: {last_scraped}
last_verified: {today}
---

# {name} ({handle})

## Profile

- **Handle:** {handle}
- **Platform:** Instagram
- **Profile URL:** {url}
- **Follower Count:** {followers}
- **Region:** {region}
- **Language:** {language}

## AI / Content

- **AIGC Verdict:** {aigc}
- **Primary AI Tool:** {primary_tool if primary_tool and primary_tool not in ('nan', '') else 'Unknown'}
- **Tags:** {tags}

## Contact

- **Email:** {email_final if email_final and email_final not in ('nan', 'not exposed', '') else 'Not publicly available'}
"""
    if email_final and email_final not in ('nan', 'not exposed', ''):
        note_content += f"- **Contact Source:** {contact_url if contact_url and contact_url not in ('nan', '') else url}\n"
    else:
        note_content += f"- **Contact Source:** {url}\n"
    
    note_content += f"""
## Evidence

- **Source:** {source}
- **Scraped At:** {last_scraped}
- **Bio Preview:** {bio_text[:200] if bio_text else 'N/A'}

## Notes

{notes}

## Related

- [[Platforms/Instagram]]
- [[Daily/{today}]]
"""
    
    with open(note_path, 'w') as f:
        f.write(note_content)
    
    if note_exists:
        notes_updated += 1
        print(f"  UPDATED NOTE: {handle_clean}.md")
    else:
        notes_created += 1
        print(f"  CREATED NOTE: {handle_clean}.md")

crm.to_csv(crm_path, index=False)
print(f"\n=== CRM: {len(crm)} total ({updated_crm} updated, {new_crm} new) ===")
print(f"=== Obsidian: {notes_created} created, {notes_updated} updated ===")
