import os
import sys
import subprocess

def run_cmd(command):
    print(f"\n>> EXEC: {command}")
    ret = os.system(command)
    if ret != 0:
        print(f"!! ERROR: Command failed with code {ret}")
        sys.exit(ret)

def main():
    print("=== [PHASE 1] EXPERIMENTATION ===")
    print("Goal: Validate model on split data (Train/Test) before production.")
    
    # 1. Split Data
    print("\n1. Splitting 'enriched_logs.csv' into Train/Valid/Test...")
    run_cmd(f"{sys.executable} scripts/split_data.py")
    
    # 2. Train on TRAIN SET (80%)
    print("\n2. Training Model on TRAIN SET (Active users only)...")
    # Build Matrix from train.csv
    run_cmd(f"{sys.executable} build_interaction_matrix.py --input data/train.csv")
    # Prep & Train
    run_cmd(f"{sys.executable} prep_user_data.py")
    run_cmd(f"{sys.executable} train_user_cf.py --neighbors 50")
    
    # 3. Evaluate on TEST SET (10%)
    print("\n3. Evaluating on TEST SET (Simulating unseen future)...")
    run_cmd(f"{sys.executable} scripts/evaluate_model.py")
    
    print("\n=== EXPERIMENT COMPLETE ===")
    print("Check the metrics above. If Recall@10 < 0.3, consider tuning before deploying.")

if __name__ == "__main__":
    main()
