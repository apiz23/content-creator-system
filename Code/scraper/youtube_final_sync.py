"""YouTube scrape → CRM + Obsidian sync (correct field names)."""
import csv, json, os, re
from datetime import datetime, timezone

now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
crm_path = 'data/Creator-Intel-CRM-List.csv'
out_path = 'data/output/youtube_refreshed_output.csv'
vault = 'obsidian/Creator Research/Creators'

# Read scraper output
with open(out_path, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    scraper_rows = list(reader)
    scraper_fields = reader.fieldnames

print(f"Scraper: {len(scraper_rows)} rows")

# Read CRM
with open(crm_path, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    crm_rows = list(reader)
    crm_fields = list(reader.fieldnames) if reader.fieldnames else []

print(f"CRM before: {len(crm_rows)} rows, {len(crm_fields)} fields")
print(f"CRM fields: {crm_fields}")

# Build lookup
crm_by_url = {}
for i, row in enumerate(crm_rows):
    url = row.get('ProfileURL', '').strip().lower()
    if url:
        crm_by_url[url] = i

updated = 0
added = 0

for sr in scraper_rows:
    url = sr.get('ProfileURL', '').strip()
    if not url:
        continue
    url_key = url.lower()

    # Map scraper fields to CRM fields
    rec = {}
    for crm_key in crm_fields:
        if crm_key == 'ProfileURL':
            rec[crm_key] = url
        elif crm_key == 'Name/Handle':
            rec[crm_key] = sr.get('Name/Handle', '').strip()
        elif crm_key == 'Platform':
            rec[crm_key] = sr.get('Platform', 'YouTube').strip()
        elif crm_key == 'FollowerCount':
            fol = sr.get('FollowerCount', '').strip()
            # Preserve empty, don't write "0" for empty
            rec[crm_key] = fol if fol else ''
        elif crm_key == 'Email':
            email = sr.get('Email', '').strip()
            rec[crm_key] = email if email and email != 'not exposed' else ''
        elif crm_key == 'Tags':
            rec[crm_key] = sr.get('Tags', '').strip()
        elif crm_key == 'OutreachStatus':
            rec[crm_key] = sr.get('OutreachStatus', 'Updated').strip()
        elif crm_key == 'LastScrapedAt':
            rec[crm_key] = now_iso
        elif crm_key == 'Region':
            region = sr.get('Region', '').strip()
            rec[crm_key] = region if region and region != 'Unknown' else ''
        elif crm_key == 'Language':
            rec[crm_key] = sr.get('Language', 'en').strip() or 'en'
        elif crm_key == 'PrimaryAITool':
            rec[crm_key] = sr.get('PrimaryAITool', '').strip()
        elif crm_key == 'SampleContentURL':
            rec[crm_key] = sr.get('SampleContentURL', '').strip()
        elif crm_key == 'AIGCVerdict':
            rec[crm_key] = sr.get('AIGCVerdict', '').strip()
        elif crm_key == 'DiscoveredAt':
            rec[crm_key] = sr.get('DiscoveredAt', now_iso).strip()
        elif crm_key == 'Source':
            rec[crm_key] = sr.get('Source', '').strip()
        elif crm_key == 'Notes':
            rec[crm_key] = sr.get('Notes', '').strip()
        elif crm_key == 'FeedURL':
            rec[crm_key] = sr.get('FeedURL', '').strip()
        elif crm_key == 'ContactSourceURL':
            rec[crm_key] = sr.get('ContactSourceURL', '').strip()
        elif crm_key == 'EvidenceJSON':
            rec[crm_key] = sr.get('EvidenceJSON', '').strip()
        else:
            rec[crm_key] = ''

    if url_key in crm_by_url:
        idx = crm_by_url[url_key]
        old = crm_rows[idx]
        # Only update non-empty values
        for key, val in rec.items():
            if val and val != '0':
                old[key] = val
            elif key == 'FollowerCount' and val == '':
                # Preserve old follower count if new is empty
                pass
            elif key == 'Email' and (not val or val == 'not exposed'):
                # Preserve old email
                pass
        crm_rows[idx] = old
        updated += 1
    else:
        # New row - use rec as-is, fill missing with empty
        full_rec = {k: rec.get(k, '') for k in crm_fields}
        crm_rows.append(full_rec)
        added += 1
        crm_by_url[url_key] = len(crm_rows) - 1

with open(crm_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=crm_fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(crm_rows)

print(f"CRM after: {len(crm_rows)} rows")
print(f"  Updated: {updated}, Added: {added}")

# --- Obsidian sync ---
os.makedirs(vault, exist_ok=True)
notes_created = 0
notes_updated = 0

for sr in scraper_rows:
    url = sr.get('ProfileURL', '').strip()
    if not url:
        continue
    handle = sr.get('Name/Handle', '').strip().lstrip('@')
    fol_raw = sr.get('FollowerCount', '').strip()
    fol_display = fol_raw if fol_raw and fol_raw != '0' else 'Unknown'
    email = sr.get('Email', '').strip()
    email_display = email if email and email != 'not exposed' else 'Not publicly available'
    tags = sr.get('Tags', '').strip() or 'Unknown'
    primary = sr.get('PrimaryAITool', '').strip() or 'Unknown'
    verdict = sr.get('AIGCVerdict', '').strip()
    lang = sr.get('Language', '').strip() or 'Unknown'
    region = sr.get('Region', '').strip() or 'Unknown'
    sample = sr.get('SampleContentURL', '').strip() or url
    notes = sr.get('Notes', '').strip()

    if verdict == 'yes':
        aigc_text = 'Yes — content appears AI-generated or AI-assisted'
    elif verdict == 'no':
        aigc_text = 'No — content does not appear AI-generated'
    else:
        aigc_text = 'Unsure — insufficient data'

    fn = handle.replace('.', '_').replace('/', '_') + '.md'

    yaml = f"""---
name: {handle}
handle: {handle}
platform: YouTube
profile_url: {url}
followers: {fol_display}
email: {email_display}
category: AI Video / Generative AI / Filmmaking
language: {lang}
region: {region}
ai_tools: {primary}
status: Updated
last_verified: {now_iso}
discovered_at: {now_iso}
last_scraped_at: {now_iso}
---

# {handle}

## Profile

- **Handle:** {handle}
- **Platform:** YouTube
- **Profile URL:** {url}
- **Follower Count:** {fol_display}

## AI / Content

- **AIGC Verdict:** {aigc_text}
- **Primary AI Tool:** {primary}
- **Language:** {lang}
- **Tags:** {tags}

## Contact

- **Email:** {email_display}

## Evidence

- **Source URL:** {url}
- **Sample Content:** {sample}

"""

    if notes:
        yaml += f"\n## Notes\n\n{notes}\n"

    yaml += f"\n## Related\n\n- [[Platforms/YouTube]]\n- [[Daily/2026-09-03]]\n"

    path = os.path.join(vault, fn)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            existing = f.read()
        if existing.strip() != yaml.strip():
            with open(path, 'w', encoding='utf-8') as f:
                f.write(yaml)
            notes_updated += 1
    else:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(yaml)
        notes_created += 1

print(f"Obsidian: {notes_created} created, {notes_updated} updated")

# Summary
yt_count = len([r for r in crm_rows if r.get('Platform', '') == 'YouTube'])
with_fol = len([r for r in scraper_rows if r.get('FollowerCount', '').strip() and r.get('FollowerCount', '') != '0'])
without_fol = len([r for r in scraper_rows if not r.get('FollowerCount', '').strip() or r.get('FollowerCount', '') == '0'])

print(f"""
=== YOUTUBE SCRAPE FINAL REPORT ===
Output CSV: {len(scraper_rows)} rows
  With follower counts: {with_fol}
  Without follower data: {without_fol}
CRM: {len(crm_rows)} total rows ({yt_count} YouTube)
  Updated: {updated}
  Added: {added}
Obsidian: {notes_created} new + {notes_updated} updated creator notes
""")
