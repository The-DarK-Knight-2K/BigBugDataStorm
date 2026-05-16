# Data Forensics and Decision Log: Silver Layer

*This document outlines the data engineering decisions, anomaly detections, and forensics applied to transition raw Data Storm 7.0 datasets into the clean, ML-ready Silver Layer.*

## Overview: The Data Quality (DQ) Engine
Instead of ad-hoc cleaning scripts, we implemented a robust, modular Validation Engine (`pipeline/silver/dq_checks.py`). 
*   **The Decision**: Every dataset passes through strict parameterizable checks (duplicates, nulls, referential integrity, range bounds, format Regex, and valid value sets).
*   **The "Why"**: This architecture ensures all rejected rows are captured systematically into a `Data/Quarantine/` database with a specific `failure_reason`. It provides a 100% auditable pipeline rather than silently dropping valuable data.

---

## 1. Outlet Master Normalization (`clean_outlets.py`)
*   **Pipeline Metrics**: 20,000 input rows → 20,000 clean rows (0 quarantined). 196 missing sizes imputed, 785 typos canonicalized.
*   **Forensics Applied**: Identified significant inconsistencies in `Outlet_Size` (e.g., lowercase "small", and 196 missing values) and `Outlet_Type` (typos like "Grocry" and "Bakry", plus whitespace issues like " Eatery ").
*   **The "Why"**: 
    *   *Whitespace & Typos*: Canonicalized via a strict `config.yaml` mapping. This prevents dummy-variable explosion in our ML models.
    *   *Size Imputation*: Instead of dropping the 196 outlets with missing sizes, we imputed them based on `Cooler_Count`. The business logic assumes that the number of coolers highly correlates with store size (e.g., 0-1 coolers = Small, 5 coolers = Extra Large), salvaging critical data points.

## 2. Geospatial Corrections (`clean_coordinates.py`)
*   **Pipeline Metrics**: 20,000 input rows → 19,960 clean rows (40 quarantined due to zero coordinates). 200 swapped Latitude/Longitude pairs corrected.
*   **Forensics Applied**: Detected ~200 rows where `Latitude` values exceeded 50, and ~40 rows with exact `(0.0, 0.0)` coordinates.
*   **The "Why"**: 
    *   Sri Lanka's Latitude is between 5.9 and 9.9. A Latitude of 79+ indicates a human field-entry error where Latitude and Longitude were swapped. We programmatically detected and reversed these to rescue the data.
    *   Coordinates of exactly `(0.0, 0.0)` represent GPS read failures. These are quarantined so they do not skew downstream POI (Point of Interest) geographic scraping logic.

## 3. Future Extrapolation (`clean_seasonality.py`)
*   **Pipeline Metrics**: 360 input rows → 370 clean rows (Extrapolated January 2026 seasonality metrics for 10 distributors).
*   **Forensics Applied**: The raw data only contained seasonality indices up to December 2025. However, the hackathon target variable is January 2026.
*   **The "Why"**: Machine learning models cannot predict a future target if mandatory features (like Seasonality) are null for that future month. We made the defensible business assumption that FMCG cyclical seasonality remains stable year-over-year. Thus, we synthetically extrapolated the January 2025 indices forward to create the mandatory January 2026 feature rows.

## 4. Calendar Feature Engineering (`clean_holidays.py`)
*   **Pipeline Metrics**: 349 input rows → 351 clean rows. Manually injected 2 holidays for January 2026, computing 20 valid trading days for the target month.
*   **Forensics Applied**: The raw data had multiple rows per date (e.g., a date could have separate rows for "Bank" and "Mercantile" holiday types). It also lacked January 2026 data.
*   **The "Why"**:
    *   *Pivoting*: We flattened the dates to a one-hot encoded matrix (`is_public`, `is_bank`, etc.) to make it easily joinable for time-series modeling.
    *   *Manual Injection*: We manually appended the known Jan 2026 Sri Lankan holidays (Duruthu Full Moon Poya, Thai Pongal).
    *   *Trading Days*: We mathematically subtracted the holidays from the weekdays to output a `jan_2026_trading_days.json` artifact. Trading days are a heavily weighted causal factor for monthly sales volume.

## 5. Transaction Anomalies (`clean_transactions.py`)
*   **Pipeline Metrics**: 2,376,389 input rows → 2,359,769 clean rows (16,620 quarantined, 0.70% total rejection rate across negative value filters and cascading referential integrity). 140,779 records flagged as extreme volume outliers but retained.
*   **Forensics Applied**: The dataset suffered from sloppy column naming, massive volume outliers, and hidden missing data patterns.
*   **The "Why"**:
    *   *Dynamic Mapping*: Built a fuzzy-matcher to catch column drift (e.g., automatically mapping `volume_liters` to the canonical `Volume_Litres`).
    *   *Negative Volume Treatment*: 
        *   **Options Considered**: Netting at monthly level, absolute value conversion, or direct quarantine.
        *   **Decision**: We implemented a strict **Quarantine** via `range_check(min=0.01)`. This ensures that "Silver" data contains only valid purchase signals. Negative values (0.20% of data) represent returns/refunds which would otherwise skew the standard deviation of retail features.
    *   *Hierarchical Outlier Handling*: 
        *   **Options Considered**: Global Winsorization (capping), Deletion, or Contextual Flagging.
        *   **Decision**: We chose **Contextual Flagging**. We calculated the Interquartile Range (IQR) at the *individual outlet level* for stores with sufficient history, falling back to a global IQR for new stores. Values exceeding `Q3 + 5*IQR` are flagged (`is_volume_outlier`) but **NOT** quarantined. This preserves wholesale spikes for the model while allowing us to apply log-transformations later to stabilize variance.
    *   *Blackout Periods*: We isolated sequences of consecutive zero-volume months bounded by active months. Flagging these "Blackout Periods" proves to the model that these are true retail stockouts or credit-holds, not just missing database entries.

