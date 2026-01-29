import sys
import os
import numpy as np
import pandas as pd
from typing import List, Dict

# Add parent dir to path to import recommend
sys.path.append(os.getcwd())
from recommend import Recommender

def evaluate_metrics(recommender, test_df, k=10):
    """
    Compute Precision, Recall, and F1 on Test set.
    """
    hits = 0
    total_users = 0
    total_precision = 0
    total_recall = 0
    
    # Ground Truth: User -> Set(Items)
    user_ground_truth = test_df.groupby('user_id')['item_id'].apply(set).to_dict()
    unique_users = list(user_ground_truth.keys())
    
    print(f"Evaluating on {len(unique_users)} users in Test Set...")
    
    # Evaluate All Users (or sample if too large)
    # unique_users = unique_users[:2000] 
    
    cnt = 0
    for user_id in unique_users:
        truth_items = user_ground_truth[user_id]
        if len(truth_items) == 0: continue
            
        # Get Recommendations
        try:
            # We assume recommend returns top_k
            recs = recommender.recommend(user_id, top_k=k)
            rec_items = [r['item_id'] for r in recs]
        except Exception as e:
            # Cold user or error
            rec_items = []
            
        # Hit Count
        common = set(rec_items) & truth_items
        hit_count = len(common)
        
        # Metrics per user
        precision = hit_count / k
        recall = hit_count / len(truth_items) if len(truth_items) > 0 else 0
        
        total_precision += precision
        total_recall += recall
        total_users += 1
        
        cnt += 1
        if cnt % 500 == 0:
            print(f"Processed {cnt} users...")
            
    if total_users == 0:
        return 0, 0, 0
        
    avg_precision = total_precision / total_users
    avg_recall = total_recall / total_users
    f1 = 2 * (avg_precision * avg_recall) / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0
    
    return avg_precision, avg_recall, f1

def main():
    print("=== Model Evaluation ===")
    
    # 1. Load Model (Must be trained on TRAIN set)
    print("Loading Recommender...")
    rec = Recommender()
    
    # 2. Load Test Data
    if not os.path.exists('data/test.csv'):
        print("Error: data/test.csv not found.")
        return
        
    print("Loading Test Set...")
    test_df = pd.read_csv('data/test.csv')
    
    # 3. Evaluate
    k = 10
    prec, rec_score, f1 = evaluate_metrics(rec, test_df, k=k)
    
    print("\n--- Results ---")
    print(f"Precision@{k}: {prec:.4f}")
    print(f"Recall@{k}:    {rec_score:.4f}")
    print(f"F1-Score:      {f1:.4f}")
    print("---------------")

if __name__ == "__main__":
    main()
