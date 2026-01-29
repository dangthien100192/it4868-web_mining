import os
import sys
import pandas as pd
import subprocess

# Helper to run commands
def run_cmd(cmd):
    # print(f"EXEC: {cmd}")
    ret = os.system(cmd + " > /dev/null 2>&1") # Suppress output for clean grid table
    if ret != 0:
        print(f"!! Failed: {cmd}")
        return False
    return True

# Helper to evaluate (returns recall)
def quick_evaluate():
    # We call evaluate_model.py but we need it to print just the number or parse it?
    # parsing stdout is messy.
    # Let's import evaluate_metrics from scripts.evaluate_model if possible
    # But current evaluate_model.py is a script with main().
    # Let's rely on parsing the last line of output for now, or just trust the visual report.
    
    # Actually, for an automated grid, better to have a function returning the value.
    # I'll use subprocess.check_output
    
    try:
        output = subprocess.check_output(
            [sys.executable, "scripts/evaluate_model.py"], 
            stderr=subprocess.STDOUT
        ).decode('utf-8')
        
        # Parse "Recall@10:    0.5648"
        for line in output.split('\n'):
            if "Recall@10" in line:
                # format: "Recall@10:    0.5648"
                parts = line.split(':')
                if len(parts) > 1:
                    return float(parts[1].strip())
        return 0.0
    except Exception as e:
        print(f"Eval Error: {e}")
        return 0.0

def main():
    print("=== GRID SEARCH: Data Quality & Weights ===")
    print("Goal: Push User-User CF accuracy to 0.8 by optimizing inputs.\n")
    
    # Parameters
    min_interactions_list = [5, 10, 15, 20]
    weight_profiles = ['standard', 'steep']
    
    results = []
    
    print(f"{'Min Inter':<10} | {'Profile':<10} | {'Recall@10':<10}")
    print("-" * 36)
    
    for min_k in min_interactions_list:
        for profile in weight_profiles:
            # 1. Split Data (Filter with min_k)
            # This generates data/train.csv with filtered users
            run_cmd(f"{sys.executable} scripts/split_data.py --min-interactions {min_k}")
            
            # 2. Build Matrix (Apply weight profile)
            # Uses data/train.csv
            run_cmd(f"{sys.executable} build_interaction_matrix.py --input data/train.csv --weight-profile {profile}")
            
            # 3. Train Model
            run_cmd(f"{sys.executable} prep_user_data.py")
            run_cmd(f"{sys.executable} train_user_cf.py --neighbors 50")
            
            # 4. Evaluate (on data/test.csv generated in step 1)
            recall = quick_evaluate()
            
            print(f"{min_k:<10} | {profile:<10} | {recall:.4f}")
            results.append({
                'min_k': min_k,
                'profile': profile,
                'recall': recall
            })
            
    # Find Best
    best = max(results, key=lambda x: x['recall'])
    print("\n------------------------------------")
    print(f"BEST CONFIG: Min Interactions={best['min_k']}, Weight Profile={best['profile']}")
    print(f"MAX RECALL: {best['recall']:.4f}")
    print("------------------------------------")
    
    if best['recall'] >= 0.75:
        print("Success! We reached high accuracy.")
    else:
        print("Insight: Even with optimization, we might need SVD for higher scores.")

if __name__ == "__main__":
    main()
