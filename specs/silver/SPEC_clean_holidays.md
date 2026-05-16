# SPEC: clean_holidays.py

## Purpose

Read the raw holiday_list bronze parquet, parse and deduplicate dates, restructure
into one-row-per-date format with boolean type flags, sort chronologically, and
append manually defined January 2026 holidays. The clean output is used to compute
trading days and holiday count features for January 2026.

## Layer
Silver

## Inputs

| File | Path |
|------|------|
| holidays.parquet | `data/bronze/holidays.parquet` |

## Outputs

| File | Path |
|------|------|
| holidays_clean.parquet | `data/silver/holidays_clean.parquet` |
| dq_report rows | Appended to `outputs/dq_report.csv` |

---

## Known issues from data audit

| Issue | Detail | Action |
|-------|--------|--------|
| Multi-row per date | 349 rows, ~76 unique dates. Each date has 4–5 rows for different Holiday_Type values (Public, Bank, Mercantile, Poya Day) | Pivot to one row per date with boolean type columns |
| Unsorted dates | Rows not in chronological order | Sort after parsing |
| No 2026 data | File covers 2023–2025 only | Manually append known Jan 2026 holidays |
| ISO datetime format | `2023-01-06T00:00:00Z` — needs UTC parsing | Parse with `utc=True` |

---

## Step-by-step logic

### Step 1 — Load bronze

```python
df = pd.read_parquet(BRONZE / "holidays.parquet")
log.info("Loaded %d rows from holidays bronze", len(df))
```

### Step 2 — Parse dates

```python
df["date_parsed"] = pd.to_datetime(df["Date"], utc=True, errors="coerce")
```

**DQ check — unparseable dates:**
```python
bad_dates = df[df["date_parsed"].isnull()]
```
If any found: log WARNING with count. These rows cannot be used; exclude them
from further processing but do NOT write a quarantine file for this dataset —
just log them with full detail.

**Extract date only (no time):**
```python
df["date"] = df["date_parsed"].dt.date
```

### Step 3 — DQ checks on raw rows

**Check 1 — Null Holiday_Name**
```python
null_check(df, mandatory_cols=["Holiday_Name", "Holiday_Type"], dataset_name="holidays")
```
Log failures. Exclude failed rows from further processing.

**Check 2 — Valid Holiday_Type values**

Known Holiday_Type values: "Public", "Bank", "Mercantile", "Poya Day".
```python
value_set_check(df, col="Holiday_Type",
                valid_values=["Public", "Bank", "Mercantile", "Poya Day"],
                dataset_name="holidays")
```
Log any unexpected types as WARNING. Exclude them.

### Step 4 — Pivot to one row per date

The source data has multiple rows per date (one per holiday type). Restructure:

```python
def pivot_holidays(df: pd.DataFrame) -> pd.DataFrame:
    """One row per unique date with boolean columns for each holiday type."""
    result = []
    for date, group in df.groupby("date"):
        types = set(group["Holiday_Type"].str.strip().tolist())
        primary_name = group["Holiday_Name"].iloc[0]   # first name for this date
        result.append({
            "date": date,
            "Holiday_Name": primary_name,
            "is_public":     "Public"      in types,
            "is_bank":       "Bank"        in types,
            "is_mercantile": "Mercantile"  in types,
            "is_poya_day":   "Poya Day"    in types,
        })
    return pd.DataFrame(result)
```

Apply `pivot_holidays` and sort by `date`.

### Step 5 — Append January 2026 holidays manually

The source data has no 2026 entries. Based on the official Sri Lanka public holiday
calendar, append these rows:

```python
JAN_2026_HOLIDAYS = [
    {
        "date": date(2026, 1, 2),
        "Holiday_Name": "Duruthu Full Moon Poya Day",
        "is_public": True, "is_bank": True, "is_mercantile": True, "is_poya_day": True,
    },
    {
        "date": date(2026, 1, 14),
        "Holiday_Name": "Thai Pongal Day",
        "is_public": True, "is_bank": True, "is_mercantile": True, "is_poya_day": False,
    },
]
```

Add an `is_manually_added` boolean column: `True` for Jan 2026 rows, `False` for all others.

Append with `pd.concat`. Re-sort by date.

Log: "Manually added {n} January 2026 holiday entries."

> **Note for the report:** Document this manual addition in the Data Forensics
> section of the PDF report as a known gap and assumption.

### Step 6 — Cast types

```python
df_clean["date"]             = pd.to_datetime(df_clean["date"]).dt.date
df_clean["is_public"]        = df_clean["is_public"].astype(bool)
df_clean["is_bank"]          = df_clean["is_bank"].astype(bool)
df_clean["is_mercantile"]    = df_clean["is_mercantile"].astype(bool)
df_clean["is_poya_day"]      = df_clean["is_poya_day"].astype(bool)
df_clean["is_manually_added"]= df_clean["is_manually_added"].astype(bool)
```

### Step 7 — Compute January 2026 trading days (save to config output)

```python
import calendar

# All days in January 2026
jan_2026_days = pd.date_range("2026-01-01", "2026-01-31")
weekdays_jan_2026 = [d for d in jan_2026_days if d.weekday() < 5]  # Mon–Fri

jan_2026_holidays_df = df_clean[
    (pd.to_datetime(df_clean["date"]).dt.year == 2026) &
    (pd.to_datetime(df_clean["date"]).dt.month == 1)
]
holiday_dates = set(pd.to_datetime(jan_2026_holidays_df["date"]).dt.date)
trading_days = [d for d in weekdays_jan_2026 if d.date() not in holiday_dates]

jan_2026_trading_day_count = len(trading_days)
log.info("January 2026 trading days (weekdays minus holidays): %d", jan_2026_trading_day_count)
```

Save this value to `data/silver/jan_2026_trading_days.json`:
```json
{"jan_2026_trading_days": 21, "jan_2026_holiday_count": 2}
```

### Step 8 — Write output

Output columns: `[date, Holiday_Name, is_public, is_bank, is_mercantile, is_poya_day, is_manually_added]`

Write `data/silver/holidays_clean.parquet`.

---

## Assertions before writing

```python
assert df_clean["date"].duplicated().sum() == 0, "Duplicate dates in clean holidays"
assert df_clean["date"].isnull().sum() == 0
# January 2026 must have at least 2 holiday dates
jan_2026_count = (pd.to_datetime(df_clean["date"]).dt.year == 2026).sum()
assert jan_2026_count >= 2, f"Expected ≥2 Jan 2026 holidays, got {jan_2026_count}"
```

---

## CLI usage

```bash
python pipeline/silver/clean_holidays.py
```

## Dependencies

- pandas, pyarrow, pyyaml
- `pipeline.silver.dq_checks` (local import)
- Standard library: datetime, logging, json
