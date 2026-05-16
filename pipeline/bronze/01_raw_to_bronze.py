import pandas as pd
import os
import sys

# Define paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # pipeline/bronze
PIPELINE_DIR = os.path.dirname(CURRENT_DIR)              # pipeline
ROOT_DIR = os.path.dirname(PIPELINE_DIR)                 # BigBugDataStorm

# Add PIPELINE_DIR to sys.path to import utils
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from utils.logger import setup_logger

RAW_DIR = os.path.join(ROOT_DIR, 'Data', 'Raw')
BRONZE_DIR = os.path.join(ROOT_DIR, 'Data', 'Bronze')

# List of target datasets
files_to_ingest = [
    'distributor_seasonality_details.csv',
    'holiday_list.csv',
    'outlet_coordinates.csv',
    'outlet_master.csv',
    'transactions_history_final.csv'
]

def ingest_raw_to_bronze():
    log = setup_logger("01_raw_to_bronze")
    
    log.info("========================================")
    log.info("Starting Raw to Bronze Ingestion...")
    log.info("========================================")
    
    # Ensure Bronze directory exists
    os.makedirs(BRONZE_DIR, exist_ok=True)
    
    for file_name in files_to_ingest:
        raw_path = os.path.join(RAW_DIR, file_name)
        base_name = os.path.splitext(file_name)[0]
        bronze_path = os.path.join(BRONZE_DIR, f"{base_name}.parquet")
        
        if not os.path.exists(raw_path):
            log.warning(f"File not found: {raw_path}")
            continue
            
        try:
            log.info(f"Reading CSV: {file_name}")
            df = pd.read_csv(raw_path)
            
            log.info(f"Saving to Parquet: {base_name}.parquet")
            df.to_parquet(bronze_path, engine='pyarrow', index=False)
            
            log.info(f"Successfully processed {file_name}")
        except Exception as e:
            log.error(f"Failed to process {file_name}: {e}")

    log.info("========================================")
    log.info("Ingestion Complete.")
    log.info("========================================")

if __name__ == "__main__":
    ingest_raw_to_bronze()
