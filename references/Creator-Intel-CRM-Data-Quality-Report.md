# Creator Intel CRM — Data Quality Report

> **Source:** `data/Creator-Intel-CRM-List.csv`
> **Last Updated:** 2026-09-09 14:30
> **Status:** Automatically generated from the current CSV data

## 1. Executive Summary

- **Total CRM Records:** 947
- **Number of Platforms:** 10
- **Best-performing Platform:** TikTok (94.6% followers, 100% language/tags)
- **Worst-performing Platform:** LinkedIn, Reddit, Civitai, Threads (100% missing key fields)
- **Most Complete Fields:** PrimaryAITool (63.9% complete), FollowerCount (30.5% complete)
- **Most Problematic Fields:** Email (87.9% empty), Language (82.7% empty), Region (84.5% empty)
- **Major Data-Quality Concerns:**
  - 4 platforms (LinkedIn, Reddit, Civitai, Threads) have 100% missing FollowerCount, Email, Region, and Language
  - Facebook has 86.1% missing FollowerCount due to Malay UI contamination in earlier scrapes
  - Instagram has 75.9% missing FollowerCount despite being a visual-first platform with public follower counts
  - 1 dead column (Unnamed: 19) exists in the CSV with 99.6% empty values

---

## 2. Data Quality by Platform

### TikTok

**Total Records:** 37

| Column | Empty | % Empty | % Complete |
|---|---:|---:|---:|
| FollowerCount | 2 | 5.4% | 94.6% |
| Email | 13 | 35.1% | 64.9% |
| Region | 13 | 35.1% | 64.9% |
| Language | 0 | 0.0% | 100.0% |
| PrimaryAITool | 0 | 0.0% | 100.0% |

**Assessment:** Good

TikTok has the highest data completeness among all platforms. Only 2 records missing follower counts. Language and PrimaryAITool are fully populated. Email and Region are missing for about a third of records, which is acceptable since TikTok doesn't always expose these fields.

---

### YouTube

**Total Records:** 80

| Column | Empty | % Empty | % Complete |
|---|---:|---:|---:|
| FollowerCount | 1 | 1.2% | 98.8% |
| Email | 4 | 5.0% | 95.0% |
| Region | 77 | 96.2% | 3.8% |
| Language | 0 | 0.0% | 100.0% |
| PrimaryAITool | 0 | 0.0% | 100.0% |

**Assessment:** Good

YouTube has excellent follower count coverage (98.8%) and fully populated Language and PrimaryAITool. Region is almost entirely missing (96.2%), but YouTube channel metadata rarely includes geographic information. Email completeness is high at 95%.

---

### Vimeo

**Total Records:** 157

| Column | Empty | % Empty | % Complete |
|---|---:|---:|---:|
| FollowerCount | 8 | 5.1% | 94.9% |
| Email | 157 | 100.0% | 0.0% |
| Region | 70 | 44.6% | 55.4% |
| Language | 157 | 100.0% | 0.0% |
| PrimaryAITool | 42 | 26.8% | 73.2% |

**Assessment:** Moderate

Vimeo has good follower count coverage (94.9%), but Email and Language are 100% missing. This is likely because Vimeo profiles don't expose email addresses via scraping, and language detection wasn't implemented for Vimeo scrapes. Region is moderately populated at 55.4%.

---

### Instagram

**Total Records:** 58

| Column | Empty | % Empty | % Complete |
|---|---:|---:|---:|
| FollowerCount | 44 | 75.9% | 24.1% |
| Email | 47 | 81.0% | 19.0% |
| Region | 45 | 77.6% | 22.4% |
| Language | 44 | 75.9% | 24.1% |
| PrimaryAITool | 36 | 62.1% | 37.9% |

**Assessment:** Moderate

Instagram has significant gaps across all fields. Only 24.1% of records have follower counts. This is surprising since Instagram is a visual-first platform with public follower counts. The low completeness suggests many records were added via discovery without subsequent scraping. Email is missing for 81% of records.

---

### Facebook

**Total Records:** 79

| Column | Empty | % Empty | % Complete |
|---|---:|---:|---:|
| FollowerCount | 68 | 86.1% | 13.9% |
| Email | 76 | 96.2% | 3.8% |
| Region | 60 | 75.9% | 24.1% |
| Language | 57 | 72.2% | 27.8% |
| PrimaryAITool | 16 | 20.3% | 79.7% |

**Assessment:** Poor

Facebook has severe data quality issues. 86.1% of follower counts are missing, largely due to Malay UI contamination in earlier scrapes where Facebook's Bahasa Malaysia interface text was captured instead of profile data. Email is almost entirely missing (96.2%). PrimaryAITool is relatively well-populated at 79.7%.

---

### Threads

**Total Records:** 79

| Column | Empty | % Empty | % Complete |
|---|---:|---:|---:|
| FollowerCount | 79 | 100.0% | 0.0% |
| Email | 79 | 100.0% | 0.0% |
| Region | 79 | 100.0% | 0.0% |
| Language | 79 | 100.0% | 0.0% |
| PrimaryAITool | 27 | 34.2% | 65.8% |

**Assessment:** Very Poor

Threads has 100% missing data for FollowerCount, Email, Region, and Language. This is because Threads is a Meta platform with no public API for profile scraping, and the scraper relies on manual discovery or cross-platform references. Only PrimaryAITool is partially populated.

---

### LinkedIn

**Total Records:** 21

| Column | Empty | % Empty | % Complete |
|---|---:|---:|---:|
| FollowerCount | 21 | 100.0% | 0.0% |
| Email | 21 | 100.0% | 0.0% |
| Region | 21 | 100.0% | 0.0% |
| Language | 21 | 100.0% | 0.0% |
| PrimaryAITool | 0 | 0.0% | 100.0% |

**Assessment:** Very Poor

LinkedIn has 100% missing data for all fields except PrimaryAITool. LinkedIn aggressively blocks scraping, making it difficult to extract follower counts and other profile data without authentication. All 21 records lack basic profile information.

---

### Reddit

**Total Records:** 190

| Column | Empty | % Empty | % Complete |
|---|---:|---:|---:|
| FollowerCount | 190 | 100.0% | 0.0% |
| Email | 190 | 100.0% | 0.0% |
| Region | 190 | 100.0% | 0.0% |
| Language | 180 | 94.7% | 5.3% |
| PrimaryAITool | 95 | 50.0% | 50.0% |

**Assessment:** Very Poor

Reddit has the second-largest record count (190) but 100% missing FollowerCount, Email, and Region. Reddit users don't have traditional follower counts (they have karma and subscribers), which explains the gap. Language is 94.7% missing, and PrimaryAITool is only 50% complete.

---

### Civitai

**Total Records:** 245

| Column | Empty | % Empty | % Complete |
|---|---:|---:|---:|
| FollowerCount | 245 | 100.0% | 0.0% |
| Email | 245 | 100.0% | 0.0% |
| Region | 245 | 100.0% | 0.0% |
| Language | 245 | 100.0% | 0.0% |
| PrimaryAITool | 126 | 51.4% | 48.6% |

**Assessment:** Very Poor

Civitai has the most records (245) but 100% missing data for FollowerCount, Email, Region, and Language. Civitai is an AI art community where profiles don't expose traditional social media metrics. PrimaryAITool is 48.6% complete, which is reasonable since the platform is AI-focused.

---

### Platform

**Total Records:** 1

| Column | Empty | % Empty | % Complete |
|---|---:|---:|---:|
| FollowerCount | 0 | 0.0% | 100.0% |
| Email | 0 | 0.0% | 100.0% |
| Region | 0 | 0.0% | 100.0% |
| Language | 0 | 0.0% | 100.0% |
| PrimaryAITool | 0 | 0.0% | 100.0% |

**Assessment:** Good

Only 1 record exists with complete data. This appears to be a test or placeholder record.

---

## 3. Platform Comparison

| Platform | Rows | Overall Quality | Key Issue |
|---|---:|---|---|
| TikTok | 37 | ✅ Excellent | 94.6% followers, 100% language/tags |
| YouTube | 80 | ✅ Good | 98.8% followers, 96.2% missing region |
| Vimeo | 157 | ⚠️ Moderate | 94.9% followers, 100% missing email/language |
| Instagram | 58 | ⚠️ Moderate | 75.9% missing followers |
| Facebook | 79 | ❌ Poor | 86.1% missing followers (Malay UI bug) |
| Threads | 79 | ❌ Very Poor | 100% missing all key fields |
| LinkedIn | 21 | ❌ Very Poor | 100% missing all key fields |
| Reddit | 190 | ❌ Very Poor | 100% missing followers/email/region |
| Civitai | 245 | ❌ Very Poor | 100% missing followers/email/region/language |

---

## 4. Field-Level Analysis

| Field | Total Records | Empty | % Empty | % Complete |
|---|---:|---:|---:|---:|
| FollowerCount | 947 | 658 | 69.5% | 30.5% |
| Email | 947 | 832 | 87.9% | 12.1% |
| Region | 947 | 800 | 84.5% | 15.5% |
| Language | 947 | 783 | 82.7% | 17.3% |
| PrimaryAITool | 947 | 342 | 36.1% | 63.9% |

**Most Complete Field:** PrimaryAITool (63.9% complete)

**Least Complete Field:** Email (87.9% empty)

---

## 5. Data Quality Findings

### Platforms with Severe Missing-Data Problems
- **Civitai** (245 rows): 100% missing followers, email, region, language
- **Reddit** (190 rows): 100% missing followers, email, region
- **Threads** (79 rows): 100% missing all key fields
- **LinkedIn** (21 rows): 100% missing all key fields

### Fields that are Consistently Populated
- **PrimaryAITool**: 63.9% complete across all platforms
- **FollowerCount**: 30.5% complete, but highly variable by platform (94.6% for TikTok vs 0% for LinkedIn)

### Fields that are Frequently Missing
- **Email**: 87.9% empty overall
- **Language**: 82.7% empty overall
- **Region**: 84.5% empty overall

### Platform-Specific Anomalies
- **Facebook**: Malay UI contamination caused 86.1% of follower counts to be unreadable. This has been partially cleaned for 9 records, but the raw output file still contains junk data.
- **YouTube**: 96.2% missing region — this is expected since YouTube channels don't expose geographic metadata.
- **Vimeo**: 100% missing email and language — Vimeo profiles don't expose these fields via scraping.

### Potential Data Collection/Import Problems
- **Dead column**: "Unnamed: 19" exists in the CSV with 99.6% empty values. This is likely an artifact from Excel exports or pandas DataFrame index columns being saved incorrectly.
- **Malay UI contamination**: The Facebook scraper captured Facebook's navigation menu text ("Lagi", "Rakan", "Foto", "Perihal") instead of actual profile bios. This happened because Facebook was set to Bahasa Malaysia during scraping.

### Suspicious or Unusual Patterns
- The "Platform" platform has only 1 record with complete data — this may be a test record or data entry error.
- Instagram has only 58 records despite being a major platform for AI creators. This suggests under-discovery or under-scraping.

---

## 6. Recommended Actions

### High Priority
1. **Clean dead columns** — Remove "Unnamed: 19" from the CSV to reduce file size and improve readability.
2. **Fix Facebook scraper** — Switch Facebook UI to English before scraping, or use targeted DOM selectors instead of reading all page text.
3. **Fill Instagram follower counts** — Instagram has public follower counts. Run a dedicated scrape for the 44 missing records.
4. **Clean facebook_scraped_output.csv** — The 9 rows still contain Malay UI junk text. Delete or re-scrape.

### Medium Priority
5. **Cross-platform data enrichment** — Many Reddit, Threads, and LinkedIn creators have Instagram/TikTok profiles. Use their linked social media to fill in missing follower counts.
6. **Scrape Instagram profiles** — Run the Instagram scraper to update the 58 records with fresh data.
7. **Vimeo email/language** — Accept that these fields are uncollectable via scraping, or find alternative data sources.

### Low Priority
8. **Civitai/LinkedIn/Reddit** — These platforms have structural limitations. Consider whether these records should remain in the CRM if they can't be enriched.
9. **Standardize platform names** — Ensure consistent naming conventions across all records.

---

## 7. Historical Changes

No historical comparison available yet.

---

## 8. Data Quality Rating Methodology

| Rating | Completeness | Description |
|---|---|---|
| **Excellent** | ≥95% complete | Near-perfect data coverage |
| **Good** | 80–94% complete | Solid data with minor gaps |
| **Moderate** | 60–79% complete | Significant gaps but usable |
| **Poor** | 40–59% complete | Major gaps, needs attention |
| **Very Poor** | <40% complete | Insufficient data for analysis |

**Note:** Ratings are based on field completeness across FollowerCount, Email, Region, Language, and PrimaryAITool. Platform-specific context should be considered when interpreting ratings. For example, YouTube's 96.2% missing region is expected since YouTube doesn't expose geographic metadata, so YouTube is still rated "Good" overall.

---

*Report automatically generated. Do not edit manually. Run the data quality check script to refresh.*
