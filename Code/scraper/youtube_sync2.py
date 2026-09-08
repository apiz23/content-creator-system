"""YouTube scrape sync to CRM + Obsidian — respects existing CRM schema."""
import csv, json, os, re
from datetime import datetime, timezone

now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
crm_path = 'data/Creator-Intel-CRM-List.csv'
out_path = 'data/output/youtube_refreshed_output.csv'
vault = 'obsidian/Creator Research/Creators'

# --- Read output ---
with open(out_path, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    scraper_rows = list(reader)

print(f"Scraper output: {len(scraper_rows)} rows")

# --- Read CRM ---
with open(crm_path, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    crm_rows = list(reader)
    crm_fields = reader.fieldnames

print(f"CRM before: {len(crm_rows)} rows")

# Build lookup by ProfileURL (lowercase)
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

    # Clean follower count
    fol_raw = sr.get('FollowerCount', '').strip()
    fol_clean = ''
    if fol_raw and fol_raw not in ('0', 'not exposed', 'N/A'):
        digits = re.sub(r'[^0-9]', '', fol_raw)
        if digits:
            fol_clean = digits

    tags = sr.get('Tags', '').strip()
    primary = sr.get('PrimaryAITool', '').strip()
    verdict = sr.get('AIGCVerdict', '').strip()
    lang = sr.get('Language', '').strip()
    region = sr.get('Region', '').strip()
    email = sr.get('Email', '').strip()
    sample = sr.get('SampleContentURL', '').strip()
    notes = sr.get('Notes', '').strip()

    rec = {
        'ProfileURL': url,
        'Name/Handle': sr.get('Name/Handle', '').strip(),
        'Platform': sr.get('Platform', 'YouTube').strip(),
        'FollowerCount': fol_clean if fol_clean else '0',
        'Email': email if email and email != 'not exposed' else '',
        'Tags': tags,
        'OutreachStatus': sr.get('OutreachStatus', 'Updated').strip(),
        'LastScrapedAt': now_iso,
        'Region': region if region and region != 'Unknown' else '',
        'Language': lang if lang else 'en',
        'PrimaryAITool': primary if primary else '',
        'SampleContentURL': sample if sample else '',
        'AIGCVerdict': verdict if verdict else '',
        'DiscoveredAt': sr.get('DiscoveredAt', now_iso).strip(),
        'Source': sr.get('Source', '').strip(),
        'Notes': notes if notes else '',
        'FeedURL': sr.get('FeedURL', '').strip(),
        'ContactSourceURL': sr.get('ContactSourceURL', '').strip(),
        'EvidenceJSON': sr.get('EvidenceJSON', '').strip(),
    }

    if url_key in crm_by_url:
        idx = crm_by_url[url_key]
        old = crm_rows[idx]
        # Preserve old data when new is empty
        for key, val in rec.items():
            if val and val != '0':
                old[key] = val
        crm_rows[idx] = old
        updated += 1
    else:
        crm_rows.append(rec)
        added += 1

with open(crm_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=crm_fields)
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
    fol_display = fol_raw if fol_raw and fol_raw != '0' and fol_raw != 'not exposed' else 'Unknown'
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
        aigc = 'Yes — content appears AI-generated or AI-assisted'
    elif verdict == 'no':
        aigc = 'No — content does not appear AI-generated'
    else:
        aigc = 'Unsure — insufficient data'

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

- **AIGC Verdict:** {aigc}
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

# --- Summary ---
yt_count = len([r for r in crm_rows if r.get('Platform', '') == 'YouTube'])
print(f"""
=== YOUTUBE SCRAPE FINAL REPORT ===
Output CSV: {len(scraper_rows)} rows
  - With follower counts: {len([r for r in scraper_rows if r.get('FollowerCount','').strip() not in ('', '0', 'not exposed')])}
  - Without follower data: {len([r for r in scraper_rows if r.get('FollowerCount','').strip() in ('', '0', 'not exposed')])}
CRM: {len(crm_rows)} total rows ({yt_count} YouTube)
  - Updated: {updated}
  - Added: {added}
Obsidian: {notes_created} new + {notes_updated} updated creator notes
""")
