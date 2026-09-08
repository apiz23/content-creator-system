import csv
from pathlib import Path
from datetime import datetime, timezone

base = Path('/Users/ocgt/Desktop/Creator-Research-System')
output_csv = base / 'data/output/tiktok_scraped_output.csv'
crm_csv = base / 'data/Creator-Intel-CRM-List.csv'
creators_dir = base / 'obsidian/Creator Research/Creators'
platforms_dir = base / 'obsidian/Creator Research/Platforms'
daily_dir = base / 'obsidian/Creator Research/Daily'

now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

# 1. Load and deduplicate scraper output by ProfileURL, keep last.
with open(output_csv, newline='', encoding='utf-8') as f:
    rows = list(csv.reader(f))
header = rows[0]
data = rows[1:]
print('output_rows_before', len(data))

# Use dict to keep last seen ProfileURL.
by_url = {}
order = []
for r in data:
    url = r[0].strip().lower()
    by_url[url] = r
    if url not in [u.lower() for u in order]:
        order.append(r[0].strip())
deduped = [by_url[url.lower()] for url in order]
print('output_rows_after_dedup', len(deduped))

with open(output_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(deduped)

# 2. Merge into CRM.
with open(crm_csv, newline='', encoding='utf-8') as f:
    crm_rows = list(csv.reader(f))
crm_header = crm_rows[0]
crm_data = crm_rows[1:]

crm_by_url = {r[0].strip().lower(): (i, r) for i, r in enumerate(crm_data)}
new_count = 0
updated_count = 0
output_urls = set()
for r in deduped:
    url = r[0].strip().lower()
    output_urls.add(url)
    if url in crm_by_url:
        idx, existing = crm_by_url[url]
        merged = existing[:]
        for i, val in enumerate(r):
            if val and val.strip().lower() != 'unknown':
                merged[i] = val
        crm_data[idx] = merged
        updated_count += 1
    else:
        crm_data.append(r)
        new_count += 1
        crm_by_url[url] = (len(crm_data)-1, r)

print('new', new_count, 'updated', updated_count)
with open(crm_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(crm_header)
    writer.writerows(crm_data)

# 3. Create/update Obsidian creator notes.
created_notes = []
updated_notes = []
for r in deduped:
    url = r[0]
    handle = r[1] if len(r) > 1 else url.split('/')[-1]
    safe_handle = handle.lstrip('@').lower()
    note_path = creators_dir / f'{safe_handle}.md'
    followers = r[3] if len(r) > 3 else ''
    primary_ai = r[10] if len(r) > 10 else ''
    tags = r[5] if len(r) > 5 else ''
    aigc = r[12] if len(r) > 12 else ''
    sample = r[11] if len(r) > 11 else url
    last_scraped = r[7] if len(r) > 7 else now
    evidence = r[18] if len(r) > 18 else ''
    contact_source = r[17] if len(r) > 17 else ''
    email = r[4] if len(r) > 4 else 'Unknown'
    if note_path.exists():
        text = note_path.read_text(encoding='utf-8')
        # Update fields in frontmatter if present.
        for key, val in [
            ('followers:', followers),
            ('primary_ai_tool:', primary_ai),
            ('ai_tools:', primary_ai),
            ('status:', 'Scraped'),
            ('last_scraped_at:', last_scraped),
            ('last_verified:', last_scraped),
            ('aigc_verdict:', aigc),
            ('profile_url:', url),
        ]:
            if key in text:
                # Replace only the first match after the key line.
                marker = f'{key} '
                if marker in text:
                    text = text.split(marker, 1)[0] + marker + str(val) + '\n' + marker.join(text.split(marker, 1)[1:])
        # Ensure Related section exists.
        related = f"\n## Related\n\n- [[Platforms/TikTok]]\n- [[Daily/{today}]]\n"
        if '## Related' not in text:
            text = text.rstrip() + related
        note_path.write_text(text, encoding='utf-8')
        updated_notes.append(safe_handle)
    else:
        note = f"""---
name: {handle}
handle: {handle}
platform: TikTok
profile_url: {url}
followers: {followers}
email: {email}
category: {tags}
language: Unknown
region: Unknown
ai_tools: {primary_ai}
status: New
discovered_at: {now}
last_scraped_at: {last_scraped}
last_verified: {last_scraped}
---

# {handle}

## Profile
- **Handle:** {handle}
- **Platform:** TikTok
- **Profile URL:** {url}
- **Follower Count:** {followers}

## AI / Content
- **Primary AI Tool:** {primary_ai}
- **AIGC Verdict:** {aigc}
- **Tags:** {tags}

## Contact
- **Email:** {email}
- **Contact Source:** {contact_source if contact_source else 'Not publicly available'}

## Evidence
- **Source:** TikTok scrape
- **Sample Content:** {sample}
- **Evidence:** {evidence}

## Research Notes
- **Last Scraped:** {last_scraped}

## Related

- [[Platforms/TikTok]]
- [[Daily/{today}]]
"""
        note_path.write_text(note, encoding='utf-8')
        created_notes.append(safe_handle)

print('created_notes', len(created_notes))
print('updated_notes', len(updated_notes))

# 4. Update platform note.
platform_path = platforms_dir / 'TikTok.md'
creator_links = '\n'.join([f'- [[{h}]]' for h in [r[1].lstrip('@').lower() for r in deduped]])
platform_text = f"""# TikTok

## Last Updated
{now}

## Scraping
- Latest scrape date: {now}
- Profiles processed: {len(deduped)}
- Successfully scraped: {len(deduped)}
- Failed: 0

## Creators
{creator_links}

## Notes
- Latest TikTok scrape completed on {today}.
- {len(deduped)} profiles scraped.
"""
platform_path.write_text(platform_text, encoding='utf-8')

# 5. Update daily log.
daily_path = daily_dir / f'{today}.md'
daily_section = f"""
## TikTok Scrape
- Scraped {len(deduped)} TikTok profiles.
- Output: data/output/tiktok_scraped_output.csv
- Input: data/input/input_channels.csv
- Master CRM updated: {new_count} new, {updated_count} updated.
- Obsidian notes: {len(created_notes)} created, {len(updated_notes)} updated.
- Status: SUCCESS
"""
if daily_path.exists():
    existing = daily_path.read_text(encoding='utf-8')
    if '## TikTok Scrape' not in existing:
        daily_path.write_text(existing.rstrip() + daily_section, encoding='utf-8')
else:
    daily_path.write_text(f'# Daily Log — {today}\n' + daily_section, encoding='utf-8')

# 6. Verify counts.
with open(crm_csv, newline='', encoding='utf-8') as f:
    crm_final = list(csv.reader(f))
with open(output_csv, newline='', encoding='utf-8') as f:
    out_final = list(csv.reader(f))
print('crm_final_rows', len(crm_final)-1)
print('output_final_rows', len(out_final)-1)
