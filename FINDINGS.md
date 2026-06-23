# Reconciliation & Planning — Findings

_Generated 2026-06-23 from `data/sfdc_report_2026-06-22.csv` · Airtable sections pending a token in `.env`._

## Headline

- **Backlog (signed, not live, excl. Lineage):** 1,431 site services · 1,428 locations · 1,430 jobs · 137 accounts · **18,253,556 sqft**.
- **Required rate to 09/30:** ~**101 locations/week** (14 weeks left).
- **610 of 1,431 sites (43%) are already late or scheduled to miss 9/30** — 358 past target, 252 targeted after 9/30. Surfaced now, not in September.
- **Data-hygiene exposure:** 442 sites (31%) have no Job Owner; 73 have no Job Status.
- **Concentration:** top 10 accounts = 77% of site services but only 34% of sqft — coordination load and sqft exposure sit in different places.

## A · Countdown / feasibility

| Metric | Value |
| :-- | --: |
| Site services (backlog) | 1,431 |
| Locations | 1,428 |
| Jobs | 1,430 |
| Accounts | 137 |
| Backlog sqft | 18,253,556 |
| Weeks to 9/30 | 14.1 |
| **Required rate** | **101 locations/wk** |
| Trailing actual rate | _needs token_ |

### Target-go-live schedule

| Bucket | Site services | % |
| :-- | --: | --: |
| Already past target (late) | 358 | 25% |
| Targeted on/before 9/30 | 820 | 57% |
| Targeted AFTER 9/30 (will miss) | 252 | 18% |
| No target date | 1 | 0% |

## B · `dim_site` crosswalk

- 1,431 SFDC sites keyed on `18char Job ID`; Airtable record IDs fill in once the token is present. Written to `runs/dim_site.csv`.

## Planning analyses

### Readiness-gate proxy (leading indicators)

| Gate | Sites | % of backlog |
| :-- | --: | --: |
| Missing Job Owner | 442 | 31% |
| Missing Job Status | 73 | 5% |
| Missing Target Go-Live | 1 | 0% |
| Zero / missing sqft | 0 | 0% |

### Top accounts (coordination + sqft exposure)

| Account | Site services | % SS | sqft | % sqft |
| :-- | --: | --: | --: | --: |
| Rally House | 328 | 23% | 2,516,206 | 14% |
| Prime Group Holdings LLC | 167 | 12% | 833,848 | 5% |
| NextCare | 118 | 8% | 528,637 | 3% |
| Axia Women's Health | 107 | 7% | 587,747 | 3% |
| Clearway Pain Solutions | 100 | 7% | 515,382 | 3% |
| Allergy Partners PLLC | 88 | 6% | 230,901 | 1% |
| Faherty Brand | 79 | 6% | 196,781 | 1% |
| Liberty Tax | 78 | 5% | 149,000 | 1% |
| Innisfree Hotels | 23 | 2% | 57,600 | 0% |
| Crook County School District | 20 | 1% | 611,237 | 3% |

### Sqft-weighted risk

- At-risk backlog (late / no date / past 9/30): **611 sites (43%)**, **4,390,052 sqft (24% of backlog sqft)**.

### Pending Airtable token

- Trailing velocity & gap, crosswalk match rate, and cross-system drift-by-field populate automatically once `AIRTABLE_API_TOKEN` is in `.env` and the notebooks are run.
