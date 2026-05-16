import pandas as pd
import os

# Define relative paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'Data', 'Raw')
BRONZE_DIR = os.path.join(BASE_DIR, 'Data', 'Bronze')

# List of target datasets
files_to_ingest = [
    'distributor_seasonality_details.csv',
    'holiday_list.csv',
    'outlet_coordinates.csv',
    'outlet_master.csv',
    'transactions_history_final.csv'
]

def ingest_raw_to_bronze():
    print("========================================")
    print("Starting Raw to Bronze Ingestion...")
    print("========================================")
    
    # Ensure Bronze directory exists
    os.makedirs(BRONZE_DIR, exist_ok=True)
    
    for file_name in files_to_ingest:
        raw_path = os.path.join(RAW_DIR, file_name)
        base_name = os.path.splitext(file_name)[0]
        bronze_path = os.path.join(BRONZE_DIR, f"{base_name}.parquet")
        
        print(f"\nProcessing: {file_name}")
        
        if not os.path.exists(raw_path):
            print(f"  [WARNING] File not found: {raw_path}")
            continue
            
        try:
            print(f"  - Reading CSV...")
            df = pd.read_csv(raw_path)
            
            print(f"  - Saving to Parquet...")
            df.to_parquet(bronze_path, engine='pyarrow', index=False)
            
            print(f"  [SUCCESS] Saved {base_name}.parquet successfully!")
        except Exception as e:
            print(f"  [ERROR] Failed to process {file_name}: {e}")

    print("\n========================================")
    print("Ingestion Complete.")
    print("========================================")

if __name__ == "__main__":
    ingest_raw_to_bronze()
