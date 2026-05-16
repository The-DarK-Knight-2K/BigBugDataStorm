# Data Forensics and Decision Log: Silver Layer

*This document outlines the data engineering decisions, anomaly detections, and forensics applied to transition raw Data Storm 7.0 datasets into the clean, ML-ready Silver Layer.*

## Overview: The Data Quality (DQ) Engine
Instead of ad-hoc cleaning scripts, we implemented a robust, modular Validation Engine (`pipeline/silver/dq_checks.py`). 
*   **The Decision**: Every dataset passes through strict parameterizable checks (duplicates, nulls, referential integrity, range bounds, format Regex, and valid value sets).
*   **The "Why"**: This architecture ensures all rejected rows are captured systematically into a `Data/Quarantine/` database with a specific `failure_reason`. It provides a 100% auditable pipeline rather than silently dropping valuable data.

---

## 1. Outlet Master Normalization (`clean_outlets.py`)
*   **Forensics Applied**: Identified significant inconsistencies in `Outlet_Size` (e.g., lowercase "small", and 196 missing values) and `Outlet_Type` (typos like "Grocry" and "Bakry", plus whitespace issues like " Eatery ").
*   **The "Why"**: 
    *   *Whitespace & Typos*: Canonicalized via a strict `config.yaml` mapping. This prevents dummy-variable explosion in our ML models.
    *   *Size Imputation*: Instead of dropping the 196 outlets with missing sizes, we imputed them based on `Cooler_Count`. The business logic assumes that the number of coolers highly correlates with store size (e.g., 0-1 coolers = Small, 5 coolers = Extra Large), salvaging critical data points.

## 2. Geospatial Corrections (`clean_coordinates.py`)
*   **Forensics Applied**: Detected ~200 rows where `Latitude` values exceeded 50, and ~40 rows with exact `(0.0, 0.0)` coordinates.
*   **The "Why"**: 
    *   Sri Lanka's Latitude is between 5.9 and 9.9. A Latitude of 79+ indicates a human field-entry error where Latitude and Longitude were swapped. We programmatically detected and reversed these to rescue the data.
    *   Coordinates of exactly `(0.0, 0.0)` represent GPS read failures. These are quarantined so they do not skew downstream POI (Point of Interest) geographic scraping logic.

## 3. Future Extrapolation (`clean_seasonality.py`)
*   **Forensics Applied**: The raw data only contained seasonality indices up to December 2025. However, the hackathon target variable is January 2026.
*   **The "Why"**: Machine learning models cannot predict a future target if mandatory features (like Seasonality) are null for that future month. We made the defensible business assumption that FMCG cyclical seasonality remains stable year-over-year. Thus, we synthetically extrapolated the January 2025 indices forward to create the mandatory January 2026 feature rows.

## 4. Calendar Feature Engineering (`clean_holidays.py`)
*   **Forensics Applied**: The raw data had multiple rows per date (e.g., a date could have separate rows for "Bank" and "Mercantile" holiday types). It also lacked January 2026 data.
*   **The "Why"**:
    *   *Pivoting*: We flattened the dates to a one-hot encoded matrix (`is_public`, `is_bank`, etc.) to make it easily joinable for time-series modeling.
    *   *Manual Injection*: We manually appended the known Jan 2026 Sri Lankan holidays (Duruthu Full Moon Poya, Thai Pongal).
    *   *Trading Days*: We mathematically subtracted the holidays from the weekdays to output a `jan_2026_trading_days.json` artifact. Trading days are a heavily weighted causal factor for monthly sales volume.

## 5. Transaction Anomalies (`clean_transactions.py`)
*   **Forensics Applied**: The dataset suffered from sloppy column naming, massive volume outliers, and hidden missing data patterns.
*   **The "Why"**:
    *   *Dynamic Mapping*: Built a fuzzy-matcher to catch column drift (e.g., automatically mapping `volume_liters` to the canonical `Volume_Litres`).
    *   *Outlier Flagging (IQR)*: We implemented an Interquartile Range (IQR) method at the *individual outlet level*. Extreme spikes (`> Q3 + 5*IQR`) are flagged but NOT quarantined, as they may represent genuine wholesale events that the model must learn from.
    *   *Blackout Periods*: We isolated sequences of consecutive zero-volume months bounded by active months. Flagging these "Blackout Periods" proves to the model that these are true retail stockouts or credit-holds, not just missing database entries.
