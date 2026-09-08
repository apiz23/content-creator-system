"""Post-scrape fix for YouTube: retry 404'd channels + full CRM/Obsidian sync."""
import csv, json, os, re
from datetime import datetime, timezone

now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
crm_path = 'data/Creator-Intel-CRM-List.csv'
out_path = 'data/output/youtube_refreshed_output.csv'
vault = 'obsidian/Creator Research/Creators'

# --- 1. Read current output ---
with open(out_path, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    out_fields = reader.fieldnames

print(f"Current output rows: {len(rows)}")

# --- 2. Identify 404'd channels ---
dnp_rows = []
valid_rows = []
for r in rows:
    notes = r.get('Notes', '')
    if any(kw in notes for kw in ['404', 'DNF', 'entity was not found', 'not found']):
        dnp_rows.append(r)
    else:
        valid_rows.append(r)

print(f"404/DNF rows: {len(dnp_rows)}")
for r in dnp_rows:
    url = r.get('ProfileURL', '')
    handle = r.get('Name/Handle', '')
    fol = r.get('FollowerCount', '')
    print(f"  {handle}: followers={fol}, notes={notes[:80]}")

# --- 3. Retry with yt-dlp ---
import subprocess, sys

def retry_yt_dlp(profile_url):
    """Run yt-dlp against a single YouTube channel. Returns dict or None on failure."""
    cmd = [
        '.venv/bin/yt-dlp',
        '--no-check-certificate',
        '--no-playlist',
        '--flat-playlist',
        '--skip-download',
        '--dump-json',
        '--print', '%(id)s,%(uploader)s,%(subscriber_count)s,%(title)s',
        profile_url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(',', 3)
            if len(parts) >= 3:
                sub_count = parts[2].strip()
                # yt-dlp returns subscriber_count as int string or "none"
                if sub_count and sub_count != 'none':
                    try:
                        sub_count = str(int(sub_count))
                    except:
                        sub_count = sub_count
                return {
                    'ProfileURL': profile_url,
                    'Name/Handle': parts[1].strip() if len(parts) > 1 else '',
                    'FollowerCount': sub_count,
                    'Notes': f'Retried via yt-dlp at {now_iso}'
                }
    except Exception as e:
        return None
    return None

# Deduplicate by URL
seen_urls = set()
unique_dnp = []
for r in dnp_rows:
    url = r.get('ProfileURL', '').strip().lower()
    if url and url not in seen_urls:
        seen_urls.add(url)
        unique_dnp.append(r)

print(f"\nUnique 404 channels to retry: {len(unique_dnp)}")
for r in unique_dnp:
    print(f"  Retry: {r.get('ProfileURL','')}")

retried = []
for r in unique_dnp:
    url = r.get('ProfileURL', '')
    handle = r.get('Name/Handle', '')
    print(f"\nTrying yt-dlp on {handle} ({url})...")
    result = retry_yt_dlp(url)
    if result:
        retried.append(result)
        print(f"  ✓ Got: followers={result['FollowerCount']}, name={result['Name/Handle']}")
    else:
        print(f"  ✗ Failed")
        # Keep original row but mark clearly
        orig = dict(r)
        orig['Notes'] = orig.get('Notes', '') + f' [PERMANENT 404 at {now_iso}]'
        retried.append(orig)

# --- 4. Merge retried into valid rows ---
# Retain retried data, replace original DNF rows with retried versions
all_rows = valid_rows + retried
# Deduplicate by ProfileURL (keep first occurrence)
seen = {}
for r in all_rows:
    url = r.get('ProfileURL', '').strip().lower()
    if url and url not in seen:
        seen[url] = r
all_rows = list(seen.values())

print(f"\nFinal row count after merge: {len(all_rows)}")

with open(out_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=out_fields)
    writer.writeheader()
    writer.writerows(all_rows)

# --- 5. Sync to CRM ---
with open(crm_path, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    crm_rows = list(reader)
    crm_fields = reader.fieldnames

print(f"\nCRM rows before: {len(crm_rows)}")

for row in all_rows:
    url = row.get('ProfileURL', '').strip()
    if not url:
        continue
    url_key = url.lower()
    # Find existing
    idx = None
    for i, cr in enumerate(crm_rows):
        if cr.get('ProfileURL', '').strip().lower() == url_key:
            idx = i
            break

    fol = row.get('FollowerCount', '').strip()
    # Clean follower count: extract digits only
    if fol and fol != '0' and fol != 'not exposed':
        digits = re.sub(r'[^0-9]', '', fol)
        if digits:
            fol = digits
        else:
            fol = '0'
    else:
        fol = ''

    tags = row.get('Tags', '').strip()
    primary = row.get('PrimaryAITool', '').strip()
    verdict = row.get('AIGCVerdict', '').strip()
    lang = row.get('Language', '').strip()
    region = row.get('Region', '').strip()
    email = row.get('Email', '').strip()
    sample = row.get('SampleContentURL', '').strip()
    notes = row.get('Notes', '').strip()

    rec = {
        'ProfileURL': url,
        'Handle': row.get('Name/Handle', '').strip(),
        'Platform': row.get('Platform', 'YouTube').strip(),
        'FollowerCount': fol if fol else '0',
        'Email': email if email and email != 'not exposed' else '',
        'Tags': tags,
        'PrimaryAITool': primary,
        'AIGCVerdict': verdict,
        'Language': lang if lang else 'en',
        'Region': region if region else 'Unknown',
        'Notes': notes if notes else '',
        'LastScrapedAt': now_iso,
        'SampleContentURL': sample if sample else '',
    }

    if idx is not None:
        # Update existing — preserve old data if new is empty
        old = crm_rows[idx]
        for key, val in rec.items():
            if val and val != '0' and val != 'not exposed':
                old[key] = val
        crm_rows[idx] = old
        print(f"  Updated CRM: {row.get('Name/Handle','')}")
    else:
        crm_rows.append(rec)
        print(f"  Added CRM: {row.get('Name/Handle','')}")

with open(crm_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=crm_fields)
    writer.writeheader()
    writer.writerows(crm_rows)

print(f"CRM rows after: {len(crm_rows)}")

# --- 6. Obsidian sync ---
def yaml_for(row):
    name = row.get('Name/Handle', '').strip()
    handle = name
    fol = row.get('FollowerCount', '0').strip()
    email = row.get('Email', '').strip()
    tags = row.get('Tags', '').strip()
    primary = row.get('PrimaryAITool', '').strip()
    verdict = row.get('AIGCVerdict', '').strip()
    lang = row.get('Language', '').strip()
    region = row.get('Region', '').strip()
    sample = row.get('SampleContentURL', '').strip()
    notes = row.get('Notes', '').strip()
    url = row.get('ProfileURL', '').strip()

    if verdict == 'yes':
        aigc = 'Yes — content appears to be AI-generated or AI-assisted'
    elif verdict == 'no':
        aigc = 'No — content does not appear to be AI-generated'
    else:
        aigc = 'Unsure — insufficient data to determine'

    fol_display = fol if fol and fol != '0' else 'Unknown'

    email_display = email if email and email != 'not exposed' else 'Not publicly available'

    tags_str = tags if tags else 'Unknown'
    primary_str = primary if primary and primary != 'Unknown' and primary != '' else 'Unknown'
    lang_str = lang if lang else 'Unknown'
    region_str = region if region else 'Unknown'

    # Handle filename
    fn = handle.lstrip('@').replace('.', '_').replace('/', '_') + '.md'

    contact_source = ''
    if email and email != 'not exposed':
        contact_source = url

    sample_str = sample if sample else url

    notes_section = ''
    if notes:
        notes_section = f'\n## Notes\n\n{notes}\n'

    return f"""---
name: {name}
handle: {handle}
platform: YouTube
profile_url: {url}
followers: {fol_display}
email: {email_display}
category: AI Video / Generative AI / Filmmaking
language: {lang_str}
region: {region_str}
ai_tools: {primary_str}
status: {'Updated' if url in {r.get('ProfileURL','').lower() for r in crm_rows if any(r.get('ProfileURL','').strip().lower() == u for u in [row.get('ProfileURL','').strip().lower() for r in crm_rows])} else 'Discovered'}
last_verified: {now_iso}
discovered_at: {now_iso}
last_scraped_at: {now_iso}
---

# {name}

## Profile

- **Handle:** {handle}
- **Platform:** YouTube
- **Profile URL:** {url}
- **Follower Count:** {fol_display}

## AI / Content

- **AIGC Verdict:** {aigc}
- **Primary AI Tool:** {primary_str}
- **Language:** {lang_str}
- **Tags:** {tags_str}

## Contact

- **Email:** {email_display}
- **Contact Source:** {contact_source if contact_source else 'N/A'}

## Evidence

- **Source URL:** {url}
- **Sample Content:** {sample_str if sample_str else url}
- **Notes:** {notes if notes else 'N/A'}

## Related

- [[Platforms/YouTube]]
- [[Daily/2026-09-03]]
{notes_section}""", fn

os.makedirs(vault, exist_ok=True)
notes_created = 0
notes_updated = 0

for row in all_rows:
    url = row.get('ProfileURL', '').strip()
    if not url:
        continue
    content, filename = yaml_for(row)
    path = os.path.join(vault, filename)

    existing = ''
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            existing = f.read()
        if existing.strip() == content.strip():
            continue
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        notes_updated += 1
        print(f"  Updated note: {filename}")
    else:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        notes_created += 1
        print(f"  Created note: {filename}")

print(f"\nObsidian: {notes_created} created, {notes_updated} updated")

# Summary
print(f"""
=== YOUTUBE SCRAPE FINAL REPORT ===
Output: {len(all_rows)} rows in {out_path}
CRM: {len(crm_rows)} rows ({len([r for r in crm_rows if r.get('Platform','')=='YouTube'])} YouTube)
Obsidian: {notes_created} new + {notes_updated} updated creator notes
404 channels retried: {len(unique_dnp)}
Successfully retried: {len([r for r in retried if r.get('FollowerCount','') not in ('', '0', 'not exposed')])}
Failed after retry: {len([r for r in retried if r.get('FollowerCount','') in ('', '0', 'not exposed')])}
""")
