import os
import subprocess
import sys

def run_command(command):
    print(f"\n>>> Running: {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Error executing: {command}")
        sys.exit(1)

def main():
    print("=== Recommendation System Pipeline ===")
    
    # --- PHASE 1: EXPERIMENT ---
    print("\n[PHASE 1] VALIDATION EXPERIMENT")
    # This runs split -> train(80%) -> test(10%)
    # If this fails or shows bad metrics, the user can see it here.
    run_command(f"{sys.executable} scripts/run_experiment.py")
    
    print("\n" + "="*40)
    print("Experiment Passed. Proceeding to Production Build.")
    print("="*40 + "\n")
    
    # --- PHASE 2: PRODUCTION BUILD ---
    print("[PHASE 2] PRODUCTION BUILD (High Accuracy Settings)")
    print("Configuration: Min Interactions=20 | Weights=Steep | Neighbors=200")
    
    # 1. Prepare Data (Custom Filter)
    print("\n[Step 1/3] Preparing Production Data (Cleaning)...")
    run_command(f"{sys.executable} scripts/prepare_production_data.py --input enriched_logs.csv --output data/production.csv --min-interactions 20")
    
    # 2. Build Matrix (Custom Weights)
    print("\n[Step 2/3] Building Full Interaction Matrix...")
    run_command(f"{sys.executable} build_interaction_matrix.py --input data/production.csv --weight-profile steep")
    
    # 3. Train Model (Custom Neighbors)
    print("\n[Step 3/3] Training Production Model...")
    run_command(f"{sys.executable} prep_user_data.py")
    run_command(f"{sys.executable} train_user_cf.py --neighbors 200")
    
    # 4. Ready
    print("\n[SUCCESS] Pipeline Complete!")
    print("You can now start the server with:")
    print("  python app.py")

if __name__ == "__main__":
    main()
