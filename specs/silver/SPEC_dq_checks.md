# SPEC: dq_checks.py — Reusable Data Quality Check Library

## Purpose

A library of parameterizable, reusable data quality functions imported by every
`clean_*.py` script in the Silver layer. This file contains **no business logic
specific to any one dataset** — only generic, configurable checks. Every function
returns a `DQResult` named tuple so callers handle quarantine consistently.

## Layer
Silver (shared library)

## Inputs
Called programmatically by other scripts. No direct file I/O.

## Outputs
Returns `DQResult` named tuples. Does not write files.

---

## DQResult named tuple

Define at the top of the module:

```python
from typing import NamedTuple
import pandas as pd

class DQResult(NamedTuple):
    passed: pd.DataFrame    # rows that passed
    failed: pd.DataFrame    # rows that failed, with failure_reason column added
    check_name: str
    n_checked: int
    n_passed: int
    n_failed: int
```

---

## Functions to implement

---

### `duplicate_check`

```python
def duplicate_check(
    df: pd.DataFrame,
    primary_key_cols: list[str],
    dataset_name: str,
    keep: str = "first",
) -> DQResult:
```

**Logic:**
1. Identify rows where the combination of `primary_key_cols` is duplicated.
2. Mark all but the `keep` occurrence as failures.
3. Add `failure_reason = "duplicate_record"` to failed rows.
4. Return `DQResult`.

**Edge cases:**
- If `primary_key_cols` contains a column not in `df`, raise `ValueError` with a
  clear message listing the missing column.
- If `df` is empty, return a DQResult with empty passed and failed DataFrames.

---

### `null_check`

```python
def null_check(
    df: pd.DataFrame,
    mandatory_cols: list[str],
    dataset_name: str,
) -> DQResult:
```

**Logic:**
1. For each column in `mandatory_cols`, flag rows where the value is `NaN`,
   `None`, or empty string (`""`).
2. A row fails if **any** mandatory column is null/empty.
3. Add `failure_reason = "null_in_mandatory_field:{col_name}"` — include the
   specific column name that triggered the failure. If multiple columns are null
   in one row, use the first failing column name.
4. Return `DQResult`.

**Edge cases:**
- If `mandatory_cols` is empty, return all rows as passed with a WARNING log.
- Strip whitespace before checking for empty string: `str.strip() == ""`.

---

### `ref_integrity_check`

```python
def ref_integrity_check(
    df: pd.DataFrame,
    fk_col: str,
    ref_df: pd.DataFrame,
    ref_col: str,
    dataset_name: str,
) -> DQResult:
```

**Logic:**
1. Get the set of valid values: `valid = set(ref_df[ref_col].dropna())`.
2. Flag rows in `df` where `df[fk_col]` is not in `valid`.
3. Add `failure_reason = "referential_integrity_violation:{fk_col}"`.
4. Return `DQResult`.

**Edge cases:**
- Null values in `fk_col` automatically fail (a null foreign key cannot be
  validated). Use failure_reason `"null_foreign_key:{fk_col}"` for these.
- Case-sensitive comparison by default.

---

### `range_check`

```python
def range_check(
    df: pd.DataFrame,
    col: str,
    min_val: float | int | None,
    max_val: float | int | None,
    dataset_name: str,
    inclusive: bool = True,
) -> DQResult:
```

**Logic:**
1. If `min_val` is not None, flag rows where `df[col] < min_val` (or `<=` if not
   inclusive).
2. If `max_val` is not None, flag rows where `df[col] > max_val` (or `>=` if not
   inclusive).
3. A row fails if it violates either bound.
4. Add `failure_reason = "out_of_range:{col}:value={value}"` — include the actual
   offending value.
5. Return `DQResult`.

**Edge cases:**
- Null values in `col` automatically fail with reason `"null_in_range_col:{col}"`.
- If both `min_val` and `max_val` are None, log a WARNING and return all rows as
  passed.

---

### `format_check`

```python
def format_check(
    df: pd.DataFrame,
    col: str,
    regex_pattern: str,
    dataset_name: str,
) -> DQResult:
```

**Logic:**
1. Cast `col` to string.
2. Flag rows where the value does not match `regex_pattern` using `str.match()`.
3. Add `failure_reason = "format_violation:{col}:pattern={regex_pattern}"`.
4. Return `DQResult`.

**Edge cases:**
- Null values in `col` automatically fail with reason `"null_in_format_col:{col}"`.
- Use `re.fullmatch` semantics (the whole string must match, not just a substring).

---

### `value_set_check`

```python
def value_set_check(
    df: pd.DataFrame,
    col: str,
    valid_values: list[str],
    dataset_name: str,
    case_sensitive: bool = True,
) -> DQResult:
```

**Logic:**
1. Optionally normalise case: if `case_sensitive=False`, compare lowercased values.
2. Flag rows where `df[col]` is not in `valid_values`.
3. Add `failure_reason = "invalid_value:{col}:found={value}"`.
4. Return `DQResult`.

---

### `run_checks`

```python
def run_checks(
    checks: list[tuple],
    dataset_name: str,
) -> tuple[pd.DataFrame, list[pd.DataFrame]]:
```

**Purpose:** Convenience orchestrator. Runs a sequence of checks where each check
is applied to the **survivors of the previous check** (sequential filtering).

**Input:** `checks` is a list of `(function, kwargs_dict)` tuples.

**Logic:**
1. Start with the full input DataFrame from `checks[0][1]["df"]`.
2. For each check, call `function(**kwargs)`.
3. Accumulate all `failed` DataFrames in a list.
4. Pass only `passed` rows to the next check.
5. Return `(final_passed_df, list_of_failed_dfs)`.

---

### `build_dq_report_row`

```python
def build_dq_report_row(result: DQResult, dataset_name: str) -> dict:
```

**Logic:** Convert a `DQResult` to a dict matching the `dq_report.csv` schema
(see DATA_CONTRACTS.md). Used by cleaning scripts to accumulate report rows.

Returns:
```python
{
    "dataset": dataset_name,
    "check_name": result.check_name,
    "records_checked": result.n_checked,
    "records_passed": result.n_passed,
    "records_quarantined": result.n_failed,
    "failure_reasons": ", ".join(
        result.failed["failure_reason"].unique().tolist()
        if not result.failed.empty else []
    ),
}
```

---

## Logging

Each function must log at INFO level:
```
<check_name> | <dataset_name> | checked={n} passed={n} failed={n}
```

Example:
```
null_check | outlet_master | checked=20000 passed=19804 failed=196
```

---

## Dependencies

- pandas
- numpy
- Standard library: re, logging, typing

## Validation (unit test expectations)

The following must hold when this module is tested:

```python
import pandas as pd
from pipeline.silver.dq_checks import duplicate_check, null_check, range_check

# duplicate_check: 1 duplicate → 1 failed row
df = pd.DataFrame({"id": ["A", "A", "B"], "val": [1, 2, 3]})
result = duplicate_check(df, ["id"], "test")
assert result.n_failed == 1
assert result.n_passed == 2

# null_check: 1 null → 1 failed row
df = pd.DataFrame({"id": ["A", "B", "C"], "name": ["x", None, "z"]})
result = null_check(df, ["name"], "test")
assert result.n_failed == 1

# range_check: value out of range → failed
df = pd.DataFrame({"id": ["A", "B"], "score": [-1, 5]})
result = range_check(df, "score", min_val=0, max_val=10, dataset_name="test")
assert result.n_failed == 1
assert result.passed.iloc[0]["score"] == 5
```
