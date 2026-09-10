# Scraping Patterns Reference (Worked Example)

This file documents the actual engineering patterns used across one
real implementation's platform scrapers — included as a worked example
of applying `SKILL.md`'s rules in practice, not as a universal
requirement. If your project's scrapers work differently, document your
own conventions here instead; the point is having *a* reference like
this, not matching this one exactly.

## 1. Retry and error handling

**Per-record failure handling** — each record is processed
independently inside the batch loop:

```
for each input record:
    try:
        extract data
    except Exception as e:
        log error with the profile/source identifier
        mark this record as failed / skip it
    continue with next record
```

A failure for one record never aborts the entire batch. The failed
record is preserved in the original input, not silently dropped.

**No automatic retry with backoff** in this implementation — a failed
record is skipped and reported in the final counts, not requeued.

**Fallback strategy** — where an AI classification step is used, a
rule-based fallback (keyword matching) runs if the model call fails,
so a model outage degrades gracefully rather than crashing the batch.

## 2. Rate limiting and delays

Fixed inter-request delays via a simple sleep between records — no
adaptive rate limiting or backoff. Values were chosen empirically per
source to stay polite and avoid throttling; when adding a new source,
observe its tolerance and pick a conservative fixed delay.

No concurrency — sources are processed sequentially, one at a time,
to keep the implementation simple and avoid simultaneous rate limits
across records.

## 3. Extraction strategy

Three general strategies, roughly in order of preference:

1. **Public API** — most stable; use when the source offers one.
2. **Structured metadata first** (e.g. OpenGraph tags on a web page) —
   preferred over page-specific selectors because metadata tags change
   less often than UI class names.
3. **DOM/selector scraping as a fallback only** — isolate
   source-specific selectors in one function so they can be updated
   independently when a source changes its frontend.

**Stable vs. fragile, generally:** public API endpoints and structured
metadata are stable; CSS class names, custom data attributes, and exact
page-text formats are fragile and the most likely thing to break.

## 4. Output normalization

- Define every record's target schema once (a fixed column/field list)
  and enforce it on write — fill missing fields with the project's
  "unknown" placeholder rather than omitting them.
- Strip/clean input hygiene issues (stray whitespace, unnamed columns)
  at the start of every batch run.
- Merge into existing records field-by-field: an empty/unknown new
  value should never overwrite a previously verified value.

## 5. Logging conventions

Simple, consistent status prefixes work well even without a structured
logging library — e.g. a "+" prefix for progress, "-" for errors — as
long as it's consistent across every source's scraper. Report a final
count at the end of each run.

## 6. Model client usage pattern

Where a project uses an AI classification step, keep the model call
generic and provider-agnostic (see `model_client.py`-style abstraction
in `SKILL.md`'s companion code, if provided) — the scraping logic
itself should never branch on which model provider is configured, only
call a single shared function and handle its string/JSON result.

Ask for the same structured output shape from the model every time
(the same JSON keys) even when specific sources need small additions —
consistency here makes downstream merging much simpler.

## 7. Testing without touching master data

Support an optional limit (e.g. a `--limit N` flag) so a small test run
never requires editing the master input/queue file directly. Apply the
limit **in memory, after filtering**, never by writing a truncated
version back to the source file. This closes a common gap: without it,
the only way to test a change is to temporarily edit shared/master
data, which is exactly the kind of operation `SKILL.md`'s safety rules
exist to prevent.

## 8. Common anti-patterns worth avoiding

Noted here as lessons, not endorsements of the example implementation:

- Print-only logging (no structured/persisted logs) — harder to filter
  or review later.
- Hardcoded delays instead of a shared, adjustable config.
- Fragile selectors with no tests around them.
- Broad exception handling around an entire record's processing, which
  can hide unexpected failure modes.

When building a new scraper, follow whatever conventions your project
has established for consistency, but weigh whether these specific
issues are worth avoiding from the start.
