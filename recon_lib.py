"""Shared helpers + canonical config for the SFDC <-> Airtable reconciliation/planning work.

Both planning notebooks (countdown_and_crosswalk, planning_analyses) and the findings
generator import from here so field IDs and business rules live in exactly one place.
"""
import os, re, json, time, datetime as dt

try:
    import requests
except ImportError:
    requests = None
try:
    import pandas as pd
except ImportError:
    pd = None

# --------------------------------------------------------------------------------------------
# .env loading (no hard dependency on python-dotenv)
# --------------------------------------------------------------------------------------------
def load_dotenv(path=".env"):
    try:
        from dotenv import load_dotenv as _ld
        _ld(path)
        return
    except Exception:
        pass
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def get_token():
    load_dotenv()
    return (os.environ.get("AIRTABLE_API_TOKEN")
            or os.environ.get("AIRTABLE_API_KEY")
            or os.environ.get("AIRTABLE_TOKEN"))

# --------------------------------------------------------------------------------------------
# Airtable identifiers (resolved from the live schema)
# --------------------------------------------------------------------------------------------
BASE_ID  = "app7jMwevErzRNk7G"      # Command Context Sync
TABLE_ID = "tblv8G1wvbMyzJpJd"      # Job Tracking

AT_FIELDS = {
    "job_id":        "fld8yRsobul4XnOuN",  # 18char Job ID Rollup (from new_sfdc_job_sync) -- JOIN KEY
    "account":       "fldXxKR4zpyjpgEba",  # new_sfdc_account_name
    "address":       "fldtw7MdvgzEDCgFd",  # new_sfdc_concat_full_address
    "sqft":          "fld5s9VX2hp8CLr27",  # Actual Square Footage Rollup (from new_sfdc_ol_sync)
    "total_sqft":    "fld3rjmwpIisZncjZ",  # Total Sq. Ft.
    "job_status":    "fldVkbhy7xLFLWGNN",  # Job Status
    "job_type":      "fldEaFaSjZfq1BEWe",  # Job Type
    "network_live":  "fld6ehsRla0PEYvUQ",  # Network Live? (Jobs)
    "target_golive": "fldujSlIehKhZXvbN",  # Target Go-Live Date (Meter)
    "actual_golive": "fldDvLA5uaH5gWa2J",  # Actual Go-Live Date
    "is_prime":      "fld9hprabcxAZ9IWX",  # is_prime
    "connect_cust":  "fldwcdAQtzdGu8TiL",  # Connect customer?
    "job_name":      "fldWZE2JbBTALWlmg",  # Job ID (JOB-xxxx label)
}

SFDC_COLS = {
    "18char Job ID":                    "job_id",
    "Job: Account Name":                "account",
    "OL: Full Address":                 "address",
    "Actual Square Footage":            "sqft",
    "Job: Job Status":                  "job_status",
    "Job: Job Type":                    "job_type",
    "Job: Network Live?":               "network_live",
    "Job: Target Go-Live Date (Meter)": "target_golive",
    "Actual Go-Live Date":              "actual_golive",
    "Site Service: Site Service Name":  "site_service",
    "Site Service: ID":                 "site_service_id",
    "Job Name":                         "job_name",
    "ProvSite: Opportunity Name":       "opportunity",
    "Job: Job Owner":                   "owner",
    "Cellular + Connect Only":          "cellular_connect",
}

# Business rules (Focused filter set, minus the dimensions broken out as columns).
EXCLUDED_ACCOUNTS = {"Amrize", "Meter", "Lineage Logistics"}
EXCLUDED_STATUSES = {"Complete", "Canceled", "Cancelled"}
NON_FOCUSED_TYPES = {"Pre-install", "Connect-only", "Cellular-only", "NFR"}
PREINSTALL_TYPES  = {"Pre-install"}
PRIME_ACCOUNTS    = {"Prime Group Holdings LLC"}

# Program targets
GOAL_DATE = dt.date(2026, 9, 30)            # deploy everything signed (excl. Lineage) live
SQFT_GOAL_DATE = dt.date(2027, 3, 1)        # 100M sqft live total

# --------------------------------------------------------------------------------------------
# Coercion helpers
# --------------------------------------------------------------------------------------------
def norm_id(x):
    return str(x).strip().upper() if x is not None and str(x).strip() else None

def norm_text(x):
    if x is None or (pd is not None and pd.isna(x)):
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()

def to_float(x):
    if x is None or (pd is not None and pd.isna(x)) or str(x).strip() == "":
        return 0.0
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return 0.0

def to_bool_live(x):
    if isinstance(x, bool):
        return x
    return str(x).strip() in {"1", "True", "true", "Yes"}

def parse_date(s):
    s = norm_text(s)
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None

# --------------------------------------------------------------------------------------------
# Loaders
# --------------------------------------------------------------------------------------------
def load_sfdc(path, encoding="latin-1"):
    df = pd.read_csv(path, dtype=str, encoding=encoding).fillna("")
    df = df.rename(columns=SFDC_COLS)
    keep = [c for c in SFDC_COLS.values() if c in df.columns]
    df = df[keep].copy()
    df["job_id_key"]   = df["job_id"].map(norm_id)
    df["network_live"] = df["network_live"].map(to_bool_live)
    df["sqft_num"]     = df["sqft"].map(to_float)
    df["target_golive_d"] = df["target_golive"].map(parse_date)
    df["actual_golive_d"] = df["actual_golive"].map(parse_date)
    df["cellular_connect_num"] = df["cellular_connect"].map(to_float) if "cellular_connect" in df else 0.0
    df["source"] = "SFDC"
    return df

def _scalar(v):
    if isinstance(v, dict):
        return v.get("name", v.get("id"))
    if isinstance(v, list):
        return ", ".join(_scalar(x) for x in v if x is not None) if v else None
    return v

def fetch_airtable_records(field_ids, token, base_id=BASE_ID, table_id=TABLE_ID, page_size=100):
    url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
    headers = {"Authorization": f"Bearer {token}"}
    params = [("pageSize", page_size), ("returnFieldsByFieldId", "true")]
    params += [("fields[]", fid) for fid in field_ids]
    offset = None
    while True:
        p = list(params) + ([("offset", offset)] if offset else [])
        for attempt in range(5):
            r = requests.get(url, headers=headers, params=p, timeout=60)
            if r.status_code == 429:
                time.sleep(2 ** attempt); continue
            r.raise_for_status(); break
        data = r.json()
        for rec in data["records"]:
            yield rec
        offset = data.get("offset")
        if not offset:
            break

def load_airtable(token=None):
    """Return the normalized Job Tracking frame, or None if no token is available."""
    token = token or get_token()
    if not token:
        return None
    inv = {fid: name for name, fid in AT_FIELDS.items()}
    rows = []
    for rec in fetch_airtable_records(list(AT_FIELDS.values()), token):
        f = rec.get("fields", {})
        row = {"at_record_id": rec["id"]}
        for fid, name in inv.items():
            row[name] = _scalar(f.get(fid))
        rows.append(row)
    df = pd.DataFrame(rows)
    df["job_id_key"]      = df["job_id"].map(norm_id)
    df["network_live"]    = df["network_live"].map(to_bool_live)
    df["sqft_num"]        = df["sqft"].map(to_float)
    df["is_prime_num"]    = df["is_prime"].map(to_float)
    df["target_golive_d"] = df["target_golive"].map(parse_date)
    df["actual_golive_d"] = df["actual_golive"].map(parse_date)
    df["source"] = "AT"
    return df

# --------------------------------------------------------------------------------------------
# Filtering + measures (shared with the reconciliation notebook)
# --------------------------------------------------------------------------------------------
def predicate(df, *, status=None, filters="None", customer="All", type_="All", drop_prime=False):
    m = pd.Series(True, index=df.index)
    if status == "Live":
        m &= df["network_live"] == True
    elif status == "Pre-Live":
        m &= df["network_live"] == False
    if filters == "Focused":
        m &= ~df["account"].isin(EXCLUDED_ACCOUNTS)
        m &= ~df["job_status"].isin(EXCLUDED_STATUSES)
        m &= df["cellular_connect_num"] != 1
        m &= ~df["job_type"].isin(NON_FOCUSED_TYPES)
    if customer != "All":
        m &= df["account"] == customer
    if type_ == "Adjusted":
        m &= ~df["job_type"].isin(PREINSTALL_TYPES)
    elif type_ == "Pre-Install":
        m &= df["job_type"].isin(PREINSTALL_TYPES)
    if drop_prime:
        m &= ~df["account"].isin(PRIME_ACCOUNTS)
    return df[m]

def metrics(df):
    return {
        "Customers": df["account"].replace("", pd.NA).nunique(),
        "Locations": df["address"].map(norm_text).replace("", pd.NA).nunique(),
        "Rows":      len(df),
        "Jobs":      df["job_id_key"].nunique(),
        "Sqft":      int(df["sqft_num"].sum()),
    }
