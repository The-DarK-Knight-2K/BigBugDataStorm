import sqlite3
import os
import json

def verify_db():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'data', 'outlets.db')
    
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return False
        
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Count verification
    tables = ["outlets", "budget_allocations", "xai_contexts", "pipeline_health", "outlet_clusters", "cluster_pois"]
    print("\n--- Row Counts ---")
    for t in tables:
        try:
            count = cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"Table '{t}': {count} rows")
        except sqlite3.OperationalError as e:
            print(f"Error reading table '{t}': {e}")
            
    # 2. Check a sample outlet
    print("\n--- Sample Outlet Data (outlets table) ---")
    try:
        sample = cursor.execute("SELECT * FROM outlets LIMIT 1").fetchone()
        columns = [col[0] for col in cursor.description]
        if sample:
            for col, val in zip(columns, sample):
                print(f"  {col}: {val}")
        else:
            print("  No outlets found.")
    except Exception as e:
        print(f"Error querying outlets: {e}")
        
    # 3. Check a sample budget allocation
    print("\n--- Sample Budget Allocation ---")
    try:
        sample = cursor.execute("SELECT * FROM budget_allocations LIMIT 1").fetchone()
        columns = [col[0] for col in cursor.description]
        if sample:
            for col, val in zip(columns, sample):
                print(f"  {col}: {val}")
        else:
            print("  No budget allocations found.")
    except Exception as e:
        print(f"Error querying budget_allocations: {e}")
        
    # 4. Check a sample context json & check if explanation is NULL
    print("\n--- Sample Context Verification ---")
    try:
        sample = cursor.execute("SELECT outlet_id, LENGTH(context_json), xai_explanation FROM xai_contexts LIMIT 1").fetchone()
        if sample:
            oid, json_len, explanation = sample
            print(f"  outlet_id: {oid}")
            print(f"  context_json length: {json_len} chars")
            print(f"  xai_explanation: {explanation} (Expected: None)")
        else:
            print("  No XAI contexts found.")
    except Exception as e:
        print(f"Error querying xai_contexts: {e}")
        
    # 5. Check pipeline health
    print("\n--- Pipeline Health Verification ---")
    try:
        datasets = cursor.execute("SELECT dataset, records_checked, records_passed, records_quarantined FROM pipeline_health").fetchall()
        for ds, checked, passed, quarantined in datasets:
            print(f"  Dataset: {ds} | Checked: {checked} | Passed: {passed} | Quarantined: {quarantined}")
    except Exception as e:
        print(f"Error querying pipeline_health: {e}")
        
    conn.close()
    print("\nVerification complete.")
    return True

if __name__ == "__main__":
    verify_db()
