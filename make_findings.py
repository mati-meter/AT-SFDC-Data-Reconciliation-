"""Generate FINDINGS.md from the current SFDC report (and Airtable, if a token is present).

Run:  python make_findings.py [path/to/sfdc.csv]
Mirrors the computations in countdown_and_crosswalk.ipynb + planning_analyses.ipynb so the
summary always matches the notebooks.
"""
import sys, datetime as dt
import pandas as pd
import recon_lib as rl

CSV = sys.argv[1] if len(sys.argv) > 1 else "data/sfdc_report_2026-06-22.csv"
TODAY = dt.date.today()
GOAL = rl.GOAL_DATE

sfdc = rl.load_sfdc(CSV)
at = rl.load_airtable()
total_sqft = sfdc["sqft_num"].sum()
weeks_left = max((GOAL - TODAY).days / 7, 0.1)
n = len(sfdc)
locs = sfdc["address"].map(rl.norm_text).replace("", pd.NA).nunique()
req = locs / weeks_left

tg = sfdc["target_golive_d"]
past = int((tg.notna() & (tg < TODAY)).sum())
bygoal = int((tg.notna() & (tg >= TODAY) & (tg <= GOAL)).sum())
after = int((tg.notna() & (tg > GOAL)).sum())
no_tg = int(tg.isna().sum())
at_risk = past + after

gates = {
    "Missing Job Owner":      int((sfdc["owner"].map(rl.norm_text) == "").sum()),
    "Missing Job Status":     int((sfdc["job_status"].map(rl.norm_text) == "").sum()),
    "Missing Target Go-Live": int(tg.isna().sum()),
    "Zero / missing sqft":    int((sfdc["sqft_num"] == 0).sum()),
}

acct = (sfdc.groupby("account").agg(ss=("site_service", "size"), sqft=("sqft_num", "sum"))
            .sort_values("ss", ascending=False))
top10_ss = acct.head(10)["ss"].sum()
top10_sqft = acct.head(10)["sqft"].sum()

risk = sfdc[(tg.isna()) | (tg < TODAY) | (tg > GOAL)]

def pct(x, d=n): return f"{x/d*100:.0f}%"

L = []
L.append(f"# Reconciliation & Planning — Findings\n")
L.append(f"_Generated {TODAY.isoformat()} from `{CSV}`"
         + (f" + live Airtable ({len(at)} records)._\n" if at is not None
            else " · Airtable sections pending a token in `.env`._\n"))

L.append("## Headline\n")
L.append(f"- **Backlog (signed, not live, excl. Lineage):** {n:,} site services · {locs:,} locations · "
         f"{sfdc['job_id_key'].nunique():,} jobs · {sfdc['account'].replace('', pd.NA).nunique()} accounts · "
         f"**{total_sqft:,.0f} sqft**.")
L.append(f"- **Required rate to {GOAL:%m/%d}:** ~**{req:.0f} locations/week** ({weeks_left:.0f} weeks left).")
L.append(f"- **{at_risk:,} of {n:,} sites ({pct(at_risk)}) are already late or scheduled to miss 9/30** "
         f"— {past:,} past target, {after:,} targeted after 9/30. Surfaced now, not in September.")
L.append(f"- **Data-hygiene exposure:** {gates['Missing Job Owner']:,} sites ({pct(gates['Missing Job Owner'])}) "
         f"have no Job Owner; {gates['Missing Job Status']:,} have no Job Status.")
L.append(f"- **Concentration:** top 10 accounts = {pct(top10_ss)} of site services but only "
         f"{pct(top10_sqft, total_sqft)} of sqft — coordination load and sqft exposure sit in different places.\n")

L.append("## A · Countdown / feasibility\n")
L.append("| Metric | Value |")
L.append("| :-- | --: |")
L.append(f"| Site services (backlog) | {n:,} |")
L.append(f"| Locations | {locs:,} |")
L.append(f"| Jobs | {sfdc['job_id_key'].nunique():,} |")
L.append(f"| Accounts | {sfdc['account'].replace('', pd.NA).nunique()} |")
L.append(f"| Backlog sqft | {total_sqft:,.0f} |")
L.append(f"| Weeks to 9/30 | {weeks_left:.1f} |")
L.append(f"| **Required rate** | **{req:.0f} locations/wk** |")
if at is not None:
    live = at[at["actual_golive_d"].notna()]
    recent = live[live["actual_golive_d"] >= TODAY - dt.timedelta(weeks=8)]
    rate = len(recent) / 8
    gap = req - rate
    L.append(f"| Trailing actual rate (8wk) | {rate:.0f} jobs/wk |")
    L.append(f"| **Gap** | **{'on track' if gap<=0 else f'short {gap:.0f}/wk'}** |")
else:
    L.append(f"| Trailing actual rate | _needs token_ |")

L.append("\n### Target-go-live schedule\n")
L.append("| Bucket | Site services | % |")
L.append("| :-- | --: | --: |")
for label, v in [("Already past target (late)", past), ("Targeted on/before 9/30", bygoal),
                 ("Targeted AFTER 9/30 (will miss)", after), ("No target date", no_tg)]:
    L.append(f"| {label} | {v:,} | {pct(v)} |")

L.append("\n## B · `dim_site` crosswalk\n")
if at is not None:
    keyed = at.dropna(subset=["job_id_key"]).drop_duplicates("job_id_key").set_index("job_id_key")
    matched = sfdc["job_id_key"].isin(keyed.index).sum()
    L.append(f"- {n:,} SFDC sites → **{matched:,} matched to Airtable ({pct(matched)})**, "
             f"{n-matched:,} SFDC-only. Written to `runs/dim_site.csv`.")
else:
    L.append(f"- {n:,} SFDC sites keyed on `18char Job ID`; Airtable record IDs fill in once the token "
             f"is present. Written to `runs/dim_site.csv`.")

L.append("\n## Planning analyses\n")
L.append("### Readiness-gate proxy (leading indicators)\n")
L.append("| Gate | Sites | % of backlog |")
L.append("| :-- | --: | --: |")
for k, v in sorted(gates.items(), key=lambda kv: -kv[1]):
    L.append(f"| {k} | {v:,} | {pct(v)} |")

L.append("\n### Top accounts (coordination + sqft exposure)\n")
L.append("| Account | Site services | % SS | sqft | % sqft |")
L.append("| :-- | --: | --: | --: | --: |")
for a_, row in acct.head(10).iterrows():
    L.append(f"| {a_} | {int(row['ss'])} | {pct(row['ss'])} | {row['sqft']:,.0f} | {pct(row['sqft'], total_sqft)} |")

L.append("\n### Sqft-weighted risk\n")
L.append(f"- At-risk backlog (late / no date / past 9/30): **{len(risk):,} sites ({pct(len(risk))})**, "
         f"**{risk['sqft_num'].sum():,.0f} sqft ({pct(risk['sqft_num'].sum(), total_sqft)} of backlog sqft)**.")

if at is None:
    L.append("\n### Pending Airtable token\n")
    L.append("- Trailing velocity & gap, crosswalk match rate, and cross-system drift-by-field "
             "populate automatically once `AIRTABLE_API_TOKEN` is in `.env` and the notebooks are run.")

out = "FINDINGS.md"
open(out, "w").write("\n".join(L) + "\n")
print(f"Wrote {out}\n")
print("\n".join(L))
