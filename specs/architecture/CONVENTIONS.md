# Conventions — Coding Style, Logging, and Error Handling

All scripts in `pipeline/` and `modelling/` must follow these conventions exactly.
When prompting an AI agent to generate code, include this file alongside the
specific script spec.

---

## Python version

**Python 3.11** — do not use features introduced in 3.12+.

---

## File header

Every script must begin with this block:

```python
"""
<one-line description of what this script does>

Layer  : Bronze | Silver | Gold | Modelling
Inputs : <list input files>
Outputs: <list output files>
"""

import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"
with open(CONFIG_PATH) as f:
    CFG = yaml.safe_load(f)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(Path(__file__).stem)
```

---

## config.yaml structure

All paths and tunable values live in `config.yaml` at the repo root.
Scripts must never hardcode paths or thresholds.

```yaml
paths:
  raw:        data/raw
  bronze:     data/bronze
  silver:     data/silver
  gold:       data/gold
  quarantine: data/quarantine
  outputs:    outputs
  artifacts:  modelling/artifacts

files:
  transactions:  transactions_history_final.csv
  outlet_master: outlet_master.csv
  coordinates:   outlet_coordinates.csv
  seasonality:   distributor_seasonality_details.csv
  holidays:      holiday_list.csv

sri_lanka_bounds:
  lat_min: 5.9
  lat_max: 9.9
  lon_min: 79.5
  lon_max: 81.9

valid_outlet_sizes:
  - Small
  - Medium
  - Large
  - Extra Large

valid_outlet_types:
  - Hotel
  - Grocery
  - SMMT
  - Pharmacy
  - Kiosk
  - Bakery
  - Eatery

outlet_type_corrections:
  Grocry:  Grocery
  Bakry:   Bakery

seasonality_multipliers:
  Favorable:    1.20
  Moderate:     1.00
  Un-Favorable: 0.85

poi:
  radii_m: [500, 1000, 2000]
  overpass_url: https://overpass-api.de/api/interpreter
  request_delay_s: 1.5
  n_clusters: 400
  timeout_s: 60

modelling:
  random_seed: 42
  cv_folds: 5
  target_percentile: 90
  lgbm_params:
    n_estimators: 1000
    learning_rate: 0.05
    num_leaves: 63
    min_child_samples: 20
    subsample: 0.8
    colsample_bytree: 0.8
    reg_alpha: 0.1
    reg_lambda: 0.1

team_name: datastorm-teamname
```

---

## Path resolution

Always resolve paths relative to the repo root using `config.yaml` values:

```python
ROOT = Path(__file__).resolve().parents[2]   # adjust depth per script location
BRONZE = ROOT / CFG["paths"]["bronze"]
SILVER = ROOT / CFG["paths"]["silver"]
# etc.
```

---

## Logging standards

| Situation | Level |
|-----------|-------|
| Script started / finished | INFO |
| Reading / writing a file | INFO (include row count) |
| DQ check result | INFO (pass) or WARNING (fail count) |
| Records being quarantined | WARNING (include count and reason) |
| Non-fatal assumption made | WARNING |
| Fatal error before exit | ERROR |

Example:

```python
log.info("Reading outlet_master bronze: %s", path)
log.info("Loaded %d rows", len(df))
log.warning("Quarantining %d rows: %s", n, "zero_coordinates")
log.error("Cannot proceed: silver file missing: %s", path)
```

---

## Quarantine pattern

Every cleaning script follows this exact pattern. Never use `df.dropna()` silently.

```python
def quarantine(df_bad: pd.DataFrame, reason: str, store: list) -> None:
    """Append bad rows with failure_reason to the quarantine store list."""
    if df_bad.empty:
        return
    df_bad = df_bad.copy()
    df_bad["failure_reason"] = reason
    df_bad["original_row_index"] = df_bad.index
    store.append(df_bad)
    log.warning("Quarantining %d rows: %s", len(df_bad), reason)


# At end of script, write the quarantine store:
if quarantine_store:
    rejected = pd.concat(quarantine_store, ignore_index=True)
    rejected.to_parquet(QUARANTINE / "rejected_outlet_master.parquet", index=False)
    log.info("Total quarantined: %d rows", len(rejected))
else:
    log.info("No records quarantined.")
```

---

## DQ check return contract

All functions in `dq_checks.py` return a `DQResult` named tuple:

```python
from typing import NamedTuple
import pandas as pd

class DQResult(NamedTuple):
    passed: pd.DataFrame       # rows that passed the check
    failed: pd.DataFrame       # rows that failed (with failure_reason col added)
    check_name: str
    n_checked: int
    n_passed: int
    n_failed: int
```

---

## Writing parquet files

```python
df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")
log.info("Written %d rows → %s", len(df), output_path)
```

Always use `index=False`. Always use `compression="snappy"`.

---

## Script exit codes

```python
sys.exit(0)   # success
sys.exit(1)   # failure (log the error before exiting)
```

---

## Assertions before writing output

Each script must assert basic sanity before writing its output file:

```python
assert len(df_clean) > 0, "Output DataFrame is empty — aborting write."
assert "Outlet_ID" in df_clean.columns, "Outlet_ID column missing."
assert df_clean["Outlet_ID"].isnull().sum() == 0, "Null Outlet_IDs in output."
# Add dataset-specific assertions per spec
```

---

## Import order

Follow PEP 8 import ordering:
1. Standard library (`os`, `sys`, `pathlib`, `logging`, `datetime`)
2. Third-party (`pandas`, `numpy`, `yaml`, `lightgbm`)
3. Local (`from pipeline.silver.dq_checks import ...`)

Separate each group with a blank line.

---

## No Jupyter in pipeline scripts

`pipeline/` and `modelling/` scripts are plain `.py` files runnable from the
command line. Jupyter notebooks live only in `notebooks/` and are for exploration.

---

## Function length

Keep functions under 40 lines. If a function exceeds 40 lines, split it.
One function = one responsibility.

---

## Type hints

All function signatures must have type hints:

```python
def null_check(
    df: pd.DataFrame,
    mandatory_cols: list[str],
    dataset_name: str,
) -> DQResult:
```
