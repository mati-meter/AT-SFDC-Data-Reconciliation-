# AT ↔ SFDC Data Reconciliation

Reconciles **Salesforce** job/site-service data against the **Airtable** `Job Tracking` table,
reconstructing the AT-vs-SFDC comparison sheet directly from the Airtable API plus a Salesforce
report CSV — and listing every job whose attributes disagree between the two systems.

## What's here

| File | Purpose |
|---|---|
| `reconcile_sfdc_airtable.ipynb` | The reconciliation notebook (main deliverable). |
| `data/` | Drop Salesforce report CSV exports here. One row per Site Service. |
| `job_diffs.md` | Generated: the per-job attribute-difference list (gitignored). |

## Setup

```bash
pip install pandas requests jupyter
export AIRTABLE_API_TOKEN="patXXXXXXXX..."          # token with read access to the base
# optional, only for over-time attribution (Section 7):
export AIRTABLE_ENTERPRISE_ACCOUNT_ID="entXXXXXXXX"
```

## Usage

1. Export the Salesforce report (the "All site services" report with the Focused filters) to CSV
   and save it under `data/`, e.g. `data/sfdc_report_2026-06-22.csv`.
2. Open `reconcile_sfdc_airtable.ipynb`, set `SFDC_CSV_PATH` to that file, and run all cells.
3. Read `reconciliation_summary` (the AT/SFDC/Δ metric table) and `bridge` (the Adjusted-for-Prime
   delta) inline; the per-job diffs are written to `job_diffs.md`.

## How it reconciles

- **Join key:** SFDC `18char Job ID` ⇄ Airtable `18char Job ID Rollup (from new_sfdc_job_sync)`.
- **Measures (per filter combination):** distinct Customers, distinct Locations, Rows/Site
  Services, distinct Jobs, summed Sq Ft.
- **Filter dimensions** (composable, see the predicate table in the notebook): Status
  (Live / Pre-Live), Filters (None / Focused), Customer, Type (All / Adjusted / Pre-Install),
  plus the "drop Prime" bridge.

The business rules (excluded accounts/statuses, non-focused job types, Prime account) live in one
config cell so they can be adjusted when the report definition changes.

## Over-time tracking (point-in-time → diff → persist → attribute)

The notebook runs point-in-time but keeps a cheap history so you never need a full-base scan:

1. **Reconcile + diff** — per run (Sections 5–6), writing `job_diffs.md`.
2. **Persist** (Section 7) — appends the Adjusted-for-Prime metrics + diff counts to
   `runs/run_history.csv` (the trend line) and snapshots the differing job IDs to
   `runs/diffs_<timestamp>.json`.
3. **Sticky diffs** — jobs that differ in two consecutive runs. Transient sync lag clears itself
   between runs; sticky diffs are genuine drift.
4. **Attribute** (Section 8) — the Airtable **`changeEvents`** feed (cell-level before/after,
   ~14-day retention, cursor pagination) is polled + persisted to `runs/change_events.jsonl` with a
   saved cursor, then read *only* for sticky diffs to see which system moved, when, and by whom.
   Requires `AIRTABLE_ENTERPRISE_ACCOUNT_ID`. (Transition-log substrate — not the audit log.)

`.env` is auto-loaded (no `python-dotenv` required). `runs/` and `job_diffs.md` are gitignored —
they're local run state.

## Planning artifacts

Shared loaders + business rules live in `recon_lib.py` (one source of truth for field IDs), used by:

| File | Purpose |
|---|---|
| `countdown_and_crosswalk.ipynb` | **A** — countdown / feasibility baseline (backlog vs. required rate, target-date schedule, trailing velocity + gap). **B** — `dim_site` crosswalk (conformed SFDC↔AT site key → `runs/dim_site.csv`). |
| `planning_analyses.ipynb` | Backlog concentration (Pareto), readiness-gate proxy, schedule slippage, sqft-weighted risk, cross-system drift-by-field, diff aging. |
| `make_findings.py` | Regenerates `FINDINGS.md` — a one-page summary of the above — from the current CSV (`python make_findings.py [csv]`). |
| `FINDINGS.md` | Generated summary snapshot. |

SFDC-side cells run from the CSV alone; Airtable-dependent cells (velocity, crosswalk match rate,
drift) populate once `AIRTABLE_API_TOKEN` is in `.env`.

## Identifiers

- Base: `Command Context Sync` (`app7jMwevErzRNk7G`)
- Table: `Job Tracking` (`tblv8G1wvbMyzJpJd`)

Field **IDs** (not display names) are used throughout, so renaming a field in the Airtable UI
won't break the notebook.
