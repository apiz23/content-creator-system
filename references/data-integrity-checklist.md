# Data Integrity Checklist

Use before reporting a discovery or scraping run as complete.

## Discovery run
- [ ] Subject found and confirmed real / relevant to the research focus
- [ ] Profile/source URL verified
- [ ] Duplicate check completed (input queue + master dataset + knowledge base)
- [ ] Input queue updated (appended, not replaced)
- [ ] Master dataset updated (appended or merged, not replaced)
- [ ] Knowledge-base note created/updated (if applicable)
- [ ] Session/daily log updated (if the project keeps one)
- [ ] Row/entry counts verified before and after
- [ ] Result re-read from disk to confirm the write actually happened

## Scraping/extraction run
- [ ] Extraction finished for the requested source
- [ ] Raw output saved to the intermediate location
- [ ] Output verified (not empty/malformed)
- [ ] Master dataset updated per the merge rules (never wholesale replaced)
- [ ] Knowledge-base notes synced (if applicable)
- [ ] Session/daily log updated (if the project keeps one)
- [ ] Row/entry counts verified before and after
- [ ] Failed records preserved and marked, not silently dropped

If any box can't be checked, the run is not complete — report exactly
which step didn't happen and why, rather than reporting overall success.
