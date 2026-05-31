# DATA SPECIFICATION: Cooler Features & Capacity Ceilings

**Layer:** Gold
**Component:** `pipeline/gold/build_cooler_features.py`
**Output:** `Data/Gold/cooler_features.parquet`

## Overview
Generates physics-based capacity constraints for each outlet based on their physical cooler storage volume. This creates a hard ceiling for demand predictions.

## Inputs
- `Data/Silver/outlet_master_clean.parquet`
- `config.yaml` (cooler specifications)

## Logic Highlights
1. **Cooler Capacity Calculation:**
   - Base metric: `Cooler_Count` (0-5).
   - Maps each cooler to a standard physical capacity in Litres using industry-standard volumes (e.g., standard double-door cooler = 750L).
   - Introduces a scaling factor for `Outlet_Size` where larger outlets have more efficient packing density.
2. **Turnover Multiplier:**
   - Computes a theoretical maximum monthly volume based on standard shelf-replenishment rates (e.g., 3x per week = 12x per month).
3. **Capacity Utilization Ratio:**
   - Defines the structural ceiling for the outlet. Predictions exceeding this ratio represent physical impossibilities unless the outlet acquires more coolers.

## Output Schema
| Column | Type | Description |
|--------|------|-------------|
| `Outlet_ID` | `string` | Primary Key |
| `physical_capacity_litres` | `float32` | Total theoretical physical volume of all coolers |
| `max_monthly_capacity_litres`| `float32` | Maximum potential monthly throughput (Capacity × Turnover) |
| `capacity_utilization_ratio` | `float32` | Current volume / Max monthly capacity |
