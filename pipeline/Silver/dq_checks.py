import pandas as pd
import re
import logging
from typing import NamedTuple

log = logging.getLogger("pipeline")

class DQResult(NamedTuple):
    passed: pd.DataFrame
    failed: pd.DataFrame
    check_name: str
    n_checked: int
    n_passed: int
    n_failed: int

def duplicate_check(df: pd.DataFrame, primary_key_cols: list[str], dataset_name: str, keep: str = "first") -> DQResult:
    if df.empty:
        return DQResult(df, pd.DataFrame(columns=df.columns), "duplicate_check", 0, 0, 0)
    
    for col in primary_key_cols:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in dataframe for duplicate check.")
            
    duplicates = df.duplicated(subset=primary_key_cols, keep=keep)
    passed = df[~duplicates].copy()
    failed = df[duplicates].copy()
    
    if not failed.empty:
        failed["failure_reason"] = "duplicate_record"
        
    n_checked = len(df)
    n_passed = len(passed)
    n_failed = len(failed)
    
    log.info(f"duplicate_check | {dataset_name} | checked={n_checked} passed={n_passed} failed={n_failed}")
    return DQResult(passed, failed, "duplicate_check", n_checked, n_passed, n_failed)

def null_check(df: pd.DataFrame, mandatory_cols: list[str], dataset_name: str) -> DQResult:
    if df.empty:
        return DQResult(df, pd.DataFrame(columns=df.columns), "null_check", 0, 0, 0)
        
    if not mandatory_cols:
        log.warning("No mandatory columns provided for null_check.")
        return DQResult(df.copy(), pd.DataFrame(columns=df.columns), "null_check", len(df), len(df), 0)
        
    failed_mask = pd.Series(False, index=df.index)
    failed_reasons = pd.Series("", index=df.index)
    
    for col in mandatory_cols:
        # Check for NaN, None, or empty string
        is_null = df[col].isnull() | (df[col].astype(str).str.strip() == "")
        new_failures = is_null & ~failed_mask
        failed_reasons[new_failures] = f"null_in_mandatory_field:{col}"
        failed_mask = failed_mask | is_null
        
    passed = df[~failed_mask].copy()
    failed = df[failed_mask].copy()
    
    if not failed.empty:
        failed["failure_reason"] = failed_reasons[failed_mask]
        
    n_checked = len(df)
    n_passed = len(passed)
    n_failed = len(failed)
    
    log.info(f"null_check | {dataset_name} | checked={n_checked} passed={n_passed} failed={n_failed}")
    return DQResult(passed, failed, "null_check", n_checked, n_passed, n_failed)

def ref_integrity_check(df: pd.DataFrame, fk_col: str, ref_df: pd.DataFrame, ref_col: str, dataset_name: str) -> DQResult:
    if df.empty:
        return DQResult(df, pd.DataFrame(columns=df.columns), "ref_integrity_check", 0, 0, 0)
        
    valid = set(ref_df[ref_col].dropna())
    
    is_null = df[fk_col].isnull()
    is_invalid = (~is_null) & (~df[fk_col].isin(valid))
    failed_mask = is_null | is_invalid
    
    passed = df[~failed_mask].copy()
    failed = df[failed_mask].copy()
    
    if not failed.empty:
        failed.loc[is_null, "failure_reason"] = f"null_foreign_key:{fk_col}"
        failed.loc[is_invalid, "failure_reason"] = f"referential_integrity_violation:{fk_col}"
        
    n_checked = len(df)
    n_passed = len(passed)
    n_failed = len(failed)
    
    log.info(f"ref_integrity_check | {dataset_name} | checked={n_checked} passed={n_passed} failed={n_failed}")
    return DQResult(passed, failed, "ref_integrity_check", n_checked, n_passed, n_failed)

def range_check(df: pd.DataFrame, col: str, min_val: float | int | None, max_val: float | int | None, dataset_name: str, inclusive: bool = True) -> DQResult:
    if df.empty:
        return DQResult(df, pd.DataFrame(columns=df.columns), "range_check", 0, 0, 0)
        
    if min_val is None and max_val is None:
        log.warning("Both min_val and max_val are None in range_check.")
        return DQResult(df.copy(), pd.DataFrame(columns=df.columns), "range_check", len(df), len(df), 0)
        
    is_null = df[col].isnull()
    is_out_of_range = pd.Series(False, index=df.index)
    
    if min_val is not None:
        if inclusive:
            is_out_of_range = is_out_of_range | (df[col] < min_val)
        else:
            is_out_of_range = is_out_of_range | (df[col] <= min_val)
            
    if max_val is not None:
        if inclusive:
            is_out_of_range = is_out_of_range | (df[col] > max_val)
        else:
            is_out_of_range = is_out_of_range | (df[col] >= max_val)
            
    failed_mask = is_null | is_out_of_range
    passed = df[~failed_mask].copy()
    failed = df[failed_mask].copy()
    
    if not failed.empty:
        failed.loc[is_null, "failure_reason"] = f"null_in_range_col:{col}"
        failed.loc[is_out_of_range, "failure_reason"] = f"out_of_range:{col}:value=" + failed.loc[is_out_of_range, col].astype(str)
        
    n_checked = len(df)
    n_passed = len(passed)
    n_failed = len(failed)
    
    log.info(f"range_check | {dataset_name} | checked={n_checked} passed={n_passed} failed={n_failed}")
    return DQResult(passed, failed, "range_check", n_checked, n_passed, n_failed)

def format_check(df: pd.DataFrame, col: str, regex_pattern: str, dataset_name: str) -> DQResult:
    if df.empty:
        return DQResult(df, pd.DataFrame(columns=df.columns), "format_check", 0, 0, 0)
        
    is_null = df[col].isnull()
    
    # Cast to string, handling NaNs
    col_str = df[col].astype(str)
    
    # Use re.fullmatch semantics
    # str.match() determines if RE matches at beginning.
    # To get fullmatch, append $ to the regex if not already there, 
    # but pandas str.match checks from beginning, str.fullmatch exists in newer pandas
    has_match = col_str.str.fullmatch(regex_pattern)
    
    is_invalid = (~is_null) & (~has_match.fillna(False))
    failed_mask = is_null | is_invalid
    
    passed = df[~failed_mask].copy()
    failed = df[failed_mask].copy()
    
    if not failed.empty:
        failed.loc[is_null, "failure_reason"] = f"null_in_format_col:{col}"
        failed.loc[is_invalid, "failure_reason"] = f"format_violation:{col}:pattern={regex_pattern}"
        
    n_checked = len(df)
    n_passed = len(passed)
    n_failed = len(failed)
    
    log.info(f"format_check | {dataset_name} | checked={n_checked} passed={n_passed} failed={n_failed}")
    return DQResult(passed, failed, "format_check", n_checked, n_passed, n_failed)

def value_set_check(df: pd.DataFrame, col: str, valid_values: list[str], dataset_name: str, case_sensitive: bool = True) -> DQResult:
    if df.empty:
        return DQResult(df, pd.DataFrame(columns=df.columns), "value_set_check", 0, 0, 0)
        
    series_to_check = df[col]
    vals = valid_values
    
    if not case_sensitive:
        series_to_check = series_to_check.astype(str).str.lower()
        vals = [str(v).lower() for v in valid_values]
        
    is_invalid = ~series_to_check.isin(vals)
    passed = df[~is_invalid].copy()
    failed = df[is_invalid].copy()
    
    if not failed.empty:
        failed["failure_reason"] = f"invalid_value:{col}:found=" + failed[col].astype(str)
        
    n_checked = len(df)
    n_passed = len(passed)
    n_failed = len(failed)
    
    log.info(f"value_set_check | {dataset_name} | checked={n_checked} passed={n_passed} failed={n_failed}")
    return DQResult(passed, failed, "value_set_check", n_checked, n_passed, n_failed)

def run_checks(checks: list[tuple], dataset_name: str) -> tuple[pd.DataFrame, list[pd.DataFrame], list[dict]]:
    """
    Runs a sequence of checks where each check is applied to the survivors of the previous check.
    Returns (final_passed_df, list_of_failed_dfs, list_of_report_rows)
    """
    if not checks:
        return pd.DataFrame(), [], []
        
    current_df = checks[0][1]["df"]
    failed_dfs = []
    report_rows = []
    
    for func, kwargs in checks:
        kwargs["df"] = current_df
        kwargs["dataset_name"] = dataset_name
        
        result = func(**kwargs)
        current_df = result.passed
        
        if not result.failed.empty:
            failed_dfs.append(result.failed)
            
        report_rows.append(build_dq_report_row(result, dataset_name))
        
    return current_df, failed_dfs, report_rows

def build_dq_report_row(result: DQResult, dataset_name: str) -> dict:
    failure_reasons = []
    if not result.failed.empty and "failure_reason" in result.failed.columns:
        failure_reasons = result.failed["failure_reason"].unique().tolist()
        
    return {
        "dataset": dataset_name,
        "check_name": result.check_name,
        "records_checked": result.n_checked,
        "records_passed": result.n_passed,
        "records_quarantined": result.n_failed,
        "failure_reasons": ", ".join(failure_reasons)
    }
