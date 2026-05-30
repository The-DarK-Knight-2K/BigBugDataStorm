import json
import sqlite3
import os
import sys

def setup_mock_db():
    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    db_path = os.path.join(data_dir, 'outlets.db')
    
    # Path to sample_outlets.json (in docs/web_app)
    repo_root = os.path.dirname(base_dir)
    json_path = os.path.join(repo_root, 'docs', 'web_app', 'sample_outlets.json')
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        sys.exit(1)
        
    print(f"Reading mock data from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    outlets_list = data.get("outlets_list", {}).get("data", [])
    outlet_details = data.get("outlet_detail", {})
    pipeline_health = data.get("pipeline_health", {})
    
    print(f"Loaded {len(outlets_list)} outlets from outlets_list.")
    print(f"Loaded {len(outlet_details)} detailed profiles from outlet_detail.")
    
    # Create SQLite DB
    print(f"Creating database at {db_path}...")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("Removed existing outlets.db file.")
        except Exception as e:
            print(f"Warning: Could not remove existing DB file: {e}")
            
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Create outlets table
    cursor.execute('''
    CREATE TABLE outlets (
        outlet_id TEXT PRIMARY KEY,
        outlet_type TEXT NOT NULL,
        outlet_size TEXT NOT NULL,
        province TEXT NOT NULL,
        distributor_id TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        cooler_count INTEGER NOT NULL,
        predicted_potential_litres REAL NOT NULL,
        recent_3m_avg REAL NOT NULL,
        hist_p90_monthly REAL NOT NULL,
        has_transaction_history INTEGER NOT NULL,
        composite_gravity_score REAL NOT NULL,
        footfall_score REAL NOT NULL
    )
    ''')
    
    # 2. Create budget_allocations table
    cursor.execute('''
    CREATE TABLE budget_allocations (
        outlet_id TEXT PRIMARY KEY,
        uplift_gap_litres REAL NOT NULL,
        roi_score REAL NOT NULL,
        allocation_tier TEXT NOT NULL,
        trade_spend_allocation_lkr REAL NOT NULL,
        recommended_spend_type TEXT NOT NULL,
        projected_volume_uplift_litres REAL NOT NULL,
        FOREIGN KEY (outlet_id) REFERENCES outlets(outlet_id) ON DELETE CASCADE
    )
    ''')
    
    # 3. Create xai_contexts table
    cursor.execute('''
    CREATE TABLE xai_contexts (
        outlet_id TEXT PRIMARY KEY,
        context_json TEXT NOT NULL,
        xai_explanation TEXT, -- NULL by default, generated on-the-fly at runtime
        FOREIGN KEY (outlet_id) REFERENCES outlets(outlet_id) ON DELETE CASCADE
    )
    ''')
    
    # 4. Create pipeline_health table
    cursor.execute('''
    CREATE TABLE pipeline_health (
        dataset TEXT PRIMARY KEY,
        records_checked INTEGER NOT NULL,
        records_passed INTEGER NOT NULL,
        records_quarantined INTEGER NOT NULL,
        quarantine_rate REAL NOT NULL,
        check_details_json TEXT NOT NULL
    )
    ''')
    
    print("Tables created successfully.")
    
    # Begin transaction
    cursor.execute("BEGIN TRANSACTION;")
    
    try:
        # Populate outlets, budget_allocations, and xai_contexts
        for item in outlets_list:
            oid = item.get("outlet_id")
            detail = outlet_details.get(oid, {})
            
            # Fetch features from details if present, else calculate mock values based on list item
            if detail:
                lat = detail.get("latitude")
                lon = detail.get("longitude")
                cooler_count = detail.get("cooler_count", 0)
                pred = detail.get("prediction", {})
                
                predicted_potential = pred.get("Maximum_Monthly_Liters", item.get("Maximum_Monthly_Liters"))
                recent_3m_avg = pred.get("recent_3m_avg", item.get("recent_3m_avg"))
                
                sales = detail.get("sales_history", {})
                hist_p90 = sales.get("hist_p90_monthly", recent_3m_avg * 1.15)
                has_history = 1 if sales.get("active_months", 0) > 0 else 0
                
                grav = detail.get("gravity_features", {})
                composite_gravity = grav.get("composite_gravity_score", item.get("footfall_score", 50.0) * 0.9)
                
                poi = detail.get("poi_features", {})
                footfall = poi.get("footfall_score", item.get("footfall_score", 50.0))
            else:
                # No detailed item in JSON, synthesize from list item
                lat = item.get("latitude")
                lon = item.get("longitude")
                cooler_count = item.get("cooler_count", 0)
                predicted_potential = item.get("Maximum_Monthly_Liters")
                recent_3m_avg = item.get("recent_3m_avg")
                hist_p90 = round(recent_3m_avg * 1.15, 2)
                has_history = 1
                footfall = item.get("footfall_score")
                composite_gravity = round(footfall * 0.9, 2)
            
            # 1. Insert into outlets table
            cursor.execute('''
            INSERT INTO outlets (
                outlet_id, outlet_type, outlet_size, province, distributor_id,
                latitude, longitude, cooler_count, predicted_potential_litres,
                recent_3m_avg, hist_p90_monthly, has_transaction_history,
                composite_gravity_score, footfall_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                oid,
                item.get("outlet_type"),
                item.get("outlet_size"),
                item.get("province"),
                item.get("distributor_id"),
                lat,
                lon,
                cooler_count,
                predicted_potential,
                recent_3m_avg,
                hist_p90,
                has_history,
                composite_gravity,
                footfall
            ))
            
            # 2. Insert into budget_allocations table (WP only, when budget allocation is true)
            has_budget = item.get("has_budget_allocation", False)
            trade_spend_lkr = item.get("trade_spend_allocation_lkr")
            
            if has_budget and trade_spend_lkr is not None and trade_spend_lkr > 0:
                uplift_gap = item.get("uplift_gap_litres", predicted_potential - recent_3m_avg)
                
                if detail and detail.get("budget"):
                    budget_info = detail.get("budget")
                    roi_score = budget_info.get("roi_score", 0.7)
                    allocation_tier = budget_info.get("allocation_tier", "medium")
                    rec_spend_type = budget_info.get("recommended_spend_type", "discount_voucher")
                    projected_uplift = uplift_gap # Use gap as proxy
                else:
                    # Synthesize from list item budget data
                    projected_uplift = uplift_gap
                    if trade_spend_lkr >= 40000:
                        allocation_tier = "high"
                        roi_score = 0.85
                        rec_spend_type = "cooler_grant"
                    elif trade_spend_lkr >= 15000:
                        allocation_tier = "medium"
                        roi_score = 0.65
                        rec_spend_type = "discount_voucher"
                    else:
                        allocation_tier = "low"
                        roi_score = 0.35
                        rec_spend_type = "display_material"
                
                cursor.execute('''
                INSERT INTO budget_allocations (
                    outlet_id, uplift_gap_litres, roi_score, allocation_tier,
                    trade_spend_allocation_lkr, recommended_spend_type, projected_volume_uplift_litres
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    oid,
                    uplift_gap,
                    roi_score,
                    allocation_tier,
                    trade_spend_lkr,
                    rec_spend_type,
                    projected_uplift
                ))
            
            # 3. Build & Insert context_json into xai_contexts (set xai_explanation to NULL for runtime LLM execution)
            if detail:
                # Use real detail object
                # Keep explanation out to ensure dynamic on-the-fly runtime requests
                context_dict = detail.copy()
                if "explain" in context_dict:
                    del context_dict["explain"]
                context_json_str = json.dumps(context_dict, indent=2)
            else:
                # Build synthetic detailed context so frontend dashboard charts work flawlessly for non-detailed outlets
                gap = predicted_potential - recent_3m_avg
                
                # Mock shap list
                shap_values = [
                    {"feature": "transport_gravity_score", "shap_value": round(gap * 0.50, 2), "direction": "positive", "feature_value": 3.5},
                    {"feature": "footfall_score", "shap_value": round(gap * 0.30, 2), "direction": "positive", "feature_value": footfall},
                    {"feature": "hist_p90_monthly", "shap_value": round(gap * 0.20, 2), "direction": "positive", "feature_value": hist_p90},
                    {"feature": "hist_cv", "shap_value": round(gap * -0.10, 2), "direction": "negative", "feature_value": 0.10},
                    {"feature": "consecutive_zero_months_max", "shap_value": round(gap * -0.10, 2), "direction": "negative", "feature_value": 1},
                    {"feature": "months_since_last_order", "shap_value": round(gap * -0.10, 2), "direction": "negative", "feature_value": 1}
                ]
                
                synthetic_detail = {
                    "outlet_id": oid,
                    "province": item.get("province"),
                    "distributor_id": item.get("distributor_id"),
                    "outlet_type": item.get("outlet_type"),
                    "outlet_size": item.get("outlet_size"),
                    "cooler_count": cooler_count,
                    "latitude": lat,
                    "longitude": lon,
                    "coords_swapped": False,
                    "size_imputed": False,
                    "prediction": {
                        "uplift_gap_litres": round(gap, 2) if gap > 0 else 0.0,
                        "seasonality_jan_2026": "Moderate",
                        "jan_2026_trading_days": 20,
                        "jan_2026_holiday_count": 2,
                        "Maximum_Monthly_Liters": predicted_potential,
                        "recent_3m_avg": recent_3m_avg,
                        "seasonality_multiplier_jan_2026": 1.0
                    },
                    "sales_history": {
                        "hist_max_monthly": round(recent_3m_avg * 1.2, 2),
                        "hist_p90_monthly": hist_p90,
                        "hist_p75_monthly": round(recent_3m_avg * 1.05, 2),
                        "hist_mean_monthly": recent_3m_avg,
                        "hist_std_monthly": round(recent_3m_avg * 0.1, 2),
                        "hist_cv": 0.10,
                        "jan_avg_volume": recent_3m_avg,
                        "jan_max_volume": round(recent_3m_avg * 1.1, 2),
                        "jan_count": 2,
                        "active_months": 24,
                        "active_months_pct": 0.85,
                        "consecutive_zero_months_max": 1,
                        "yoy_growth_rate": 0.05,
                        "recent_3m_avg": recent_3m_avg,
                        "trend_slope": 2.5,
                        "months_since_last_order": 1,
                        "total_volume": round(recent_3m_avg * 24, 2),
                        "ema_3m": recent_3m_avg,
                        "ema_6m": recent_3m_avg
                    },
                    "poi_features": {
                        "schools_500m": 1, "schools_1000m": 3, "schools_2000m": 6,
                        "hospitals_500m": 0, "hospitals_1000m": 1, "hospitals_2000m": 2,
                        "transport_500m": 2, "transport_1000m": 4, "transport_2000m": 8,
                        "markets_500m": 1, "markets_1000m": 2, "markets_2000m": 4,
                        "worship_500m": 1, "worship_1000m": 3, "worship_2000m": 6,
                        "hospitality_500m": 1, "hospitality_1000m": 3, "hospitality_2000m": 6,
                        "footfall_score": footfall,
                        "poi_data_available": True
                    },
                    "gravity_features": {
                        "school_gravity_score": 2.00,
                        "hospital_gravity_score": 1.00,
                        "transport_gravity_score": 3.50,
                        "market_gravity_score": 1.50,
                        "worship_gravity_score": 1.50,
                        "hospitality_gravity_score": 1.50,
                        "composite_gravity_score": composite_gravity
                    },
                    "shap_values": shap_values,
                    "budget": {
                        "allocation_tier": allocation_tier if has_budget else None,
                        "roi_score": roi_score if has_budget else None,
                        "recommended_spend_type": rec_spend_type if has_budget else None,
                        "is_western_province": item.get("province") == "Western",
                        "trade_spend_allocation_lkr": trade_spend_lkr
                    } if has_budget else None
                }
                context_json_str = json.dumps(synthetic_detail, indent=2)
            
            # Write to xai_contexts (setting xai_explanation to NULL strictly per feedback)
            cursor.execute('''
            INSERT INTO xai_contexts (outlet_id, context_json, xai_explanation)
            VALUES (?, ?, NULL)
            ''', (oid, context_json_str))
            
        # 4. Insert into pipeline_health table
        datasets = pipeline_health.get("datasets", [])
        for dataset in datasets:
            cursor.execute('''
            INSERT INTO pipeline_health (
                dataset, records_checked, records_passed, records_quarantined, quarantine_rate, check_details_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                dataset.get("dataset"),
                dataset.get("records_checked"),
                dataset.get("records_passed"),
                dataset.get("records_quarantined"),
                dataset.get("quarantine_rate"),
                json.dumps(dataset.get("checks", []))
            ))
            
        conn.commit()
        print("Mock database populated successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error occurred during transaction populating, rolling back: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    setup_mock_db()
