#!/usr/bin/env python3
"""
PUMLE - Python-based Unified Machine Learning Environment
Main entry point for the application.
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from src.pumle.pumle import Pumle
from src.pumle.db import DBManager

# Load environment variables
load_dotenv()

# Application Configuration
CONFIG: Dict[str, Any] = {
    "root_path": os.path.dirname(os.path.abspath(__file__)),
    "save_metadata": False,
    "num_threads": 4,
    "saving_method": "numpy",
    "upload_to_s3": False,
    "s3_config": {
        "bucket_name": os.getenv("S3_BUCKET_NAME"),
        "aws_access_key": os.getenv("AWS_ACCESS_KEY"),
        "aws_secret_key": os.getenv("AWS_SECRET_KEY"),
        "region_name": os.getenv("AWS_REGION_NAME"),
    }
}

# Available simulation parameters
SIMULATION_PARAMETERS: List[str] = [
    "pres_ref",  # Reference pressure
    "temp_ref",  # Reference temperature
    "cp_rock",   # Rock compressibility
    "srw",       # Residual water saturation
    "src",       # Residual CO2 saturation
    "pe",        # Entry pressure
    "xnacl",     # NaCl mass fraction
    "rho_h2o",   # Water density
]

# Data lake directory structure
DATA_LAKE_DIRS: List[str] = [
    "data_lake/bronze_data",
    "data_lake/silver_data",
    "data_lake/golden_data",
    "data_lake/staging"
]

def create_data_lake_structure() -> None:
    """Create the necessary directory structure for the data lake."""
    for dir_path in DATA_LAKE_DIRS:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Created directory: {dir_path}")

def get_user_parameters() -> tuple[List[str], float]:
    """Get simulation parameters and delta variation from user input."""
    print("\n=== RUN SIMULATION ===")
    print("Available parameters:", ", ".join(SIMULATION_PARAMETERS))
    
    # Get parameters
    parameters_input = input("Enter parameters (separated by commas): ").strip()
    selected_params = [
        param.strip() 
        for param in parameters_input.split(",") 
        if param.strip() in SIMULATION_PARAMETERS
    ]
    
    if not selected_params:
        raise ValueError("No valid parameters selected")
    
    # Get delta variation
    try:
        delta_input = input("Enter delta variation: ").strip()
        delta_var = float(delta_input)
    except ValueError:
        raise ValueError("Invalid delta variation. Please enter a numeric value.")
    
    return selected_params, delta_var

def run_simulation(pumle_instance: Pumle) -> None:
    """Run the simulation with user-selected parameters."""
    create_data_lake_structure()
    
    try:
        selected_params, delta_var = get_user_parameters()
        
        # Configure simulation
        pumle_instance.config["selected_parameters"] = selected_params
        pumle_instance.config["variation_delta"] = delta_var
        
        # Run simulation
        print("[INFO] Starting pre-process...")
        pumle_instance.pre_process()
        
        print("[INFO] Pre-process done. Starting simulations...")
        pumle_instance.run_simulations()
        
        print("[INFO] Simulations finished.")
    except ValueError as e:
        print(f"[ERROR] {str(e)}")
        return

def persist_data(pumle_instance: Pumle) -> None:
    """Process and save simulation results."""
    print("\n=== PERSIST DATA ===")
    
    if not pumle_instance.configs:
        print("[INFO] No simulations found.")
        return
        
    print("[INFO] Processing results...")
    for conf in pumle_instance.configs:
        sim_hash = conf["SimNums"]["sim_hash"]
        result = pumle_instance.post_process(sim_hash)
        pumle_instance.save_data(sim_hash, result)
    
    print("[INFO] Data persisted successfully.")

def show_database() -> None:
    """Display simulation records from the database."""
    print("\n=== SHOW DATABASE ===")
    
    db = DBManager()
    query = "SELECT sim_hash, sim_id, fluid_params, status FROM simulations"
    
    with db.connect() as conn:
        rows = conn.execute(query).fetchall()
    
    if not rows:
        print("No simulations found in database.")
        return
        
    print(f"{'HASH':<12} | {'SIM_ID':<6} | {'STATUS':<10} | FLUID_PARAMS")
    print("-" * 80)
    for shash, sid, fparams, status in rows:
        print(f"{shash:<12} | {sid:<6} | {status:<10} | {fparams}")

def clean_old_files(pumle_instance: Pumle) -> None:
    """Clean up old simulation files."""
    print("\n=== CLEAN OLD FILES ===")
    pumle_instance.clean_older_files()
    print("[INFO] Old files cleaned.")

def display_menu() -> None:
    """Display the main menu."""
    os.system("clear")
    print("""
  =========================================
               P U M L E   M E N U
  =========================================
   1) Run simulation
   2) Persist data (post-process + save)
   3) Show database records
   4) Clean old files
   5) Exit
  -----------------------------------------
    """)

def main() -> None:
    """Main application entry point."""
    pumle_instance = Pumle(config=CONFIG)
    
    while True:
        display_menu()
        choice = input("Select an option: ").strip()
        
        start_time = time.time()
        
        try:
            if choice == "1":
                run_simulation(pumle_instance)
            elif choice == "2":
                persist_data(pumle_instance)
            elif choice == "3":
                show_database()
            elif choice == "4":
                clean_old_files(pumle_instance)
            elif choice == "5":
                print("\nExiting. Goodbye!\n")
                break
            else:
                print("Invalid option!")
        except Exception as e:
            print(f"[ERROR] An error occurred: {str(e)}")
        
        if choice in ["1", "2"]:
            print(f"--- {time.time() - start_time:.2f} seconds ---")
        
        input("Press Enter to continue...")

if __name__ == "__main__":
    main()
