import sys
import os
import numpy as np
import pandas as pd
from typing import List, Dict

# Add parent dir to path to import recommend
sys.path.append(os.getcwd())

# We will need to re-initialize Recommender multiple times or modify it to be lighter.
# For optimization, we only need UserUserCF and the validation logic.
from user_cf import UserUserCF
from recommend import Recommender

def evaluate_recall_at_k(recommender, valid_df, k=10, alpha=0.5):
    """
    Compute Recall@K on validation set.
    val_df: DataFrame with [user_id, item_id] columns (Ground Truth)
    """
    hits = 0
    total_users = 0
    
    # Group validation items by user
    user_ground_truth = valid_df.groupby('user_id')['item_id'].apply(set).to_dict()
    
    # Iterate through users in Validation
    # We can only evaluate users who exist in the model (Train set)
    
    unique_users = list(user_ground_truth.keys())
    
    # Sample if too many users
    if len(unique_users) > 1000:
        unique_users = np.random.choice(unique_users, 1000, replace=False)
        
    for user_id in unique_users:
        if user_id not in recommender.user_to_idx:
            continue # specific user not in train set (Cold User) - Skip for CF eval
            
        total_users += 1
        truth_items = user_ground_truth[user_id]
        
        # Get Recommendations
        # Force specific alpha
        # We need to hack/modify recommend() to accept alpha or reimplement logic here
        # Faster: invoke recommend() but we need to inject alpha. 
        # Let's Modify Recommender to accept ALPHA override? 
        # Or just reimplement the merge logic here.
        
        # 1. CF Score
        cf_recs = recommender.user_cf.recommend(user_id, k=k*2)
        cf_scores = {}
        if cf_recs:
             max_cf = max(r.get('score', 0) for r in cf_recs) if cf_recs else 1.0
             if max_cf <= 0: max_cf = 1.0
             for r in cf_recs:
                 cf_scores[r['item_id']] = r.get('score', 0) / max_cf

        # 2. Pop Score
        pop_candidates = recommender.get_popular_items_with_scores(top_k=200)
        pop_scores = {}
        if pop_candidates:
            max_pop = pop_candidates[0]['score']
            if max_pop <= 0: max_pop = 1.0
            for r in pop_candidates:
                pop_scores[r['item_id']] = r['score'] / max_pop
                
        # 3. Hybrid
        combined_candidates = set(cf_scores.keys()) | set(pop_scores.keys())
        
        # Seen filter (from Train)
        # We trust recommender.recommend logic or do simplistic one here
        
        # ... Reimplement simple Hybrid Logic ...
        final_scores = []
        for item_id in combined_candidates:
            s_cf = cf_scores.get(item_id, 0.0)
            s_pop = pop_scores.get(item_id, 0.0)
            score = (alpha * s_cf) + ((1 - alpha) * s_pop)
            final_scores.append((item_id, score))
            
        final_scores.sort(key=lambda x: x[1], reverse=True)
        top_k_recs = [x[0] for x in final_scores[:k]]
        
        # Check Hit
        if len(set(top_k_recs) & truth_items) > 0:
            hits += 1
            
    if total_users == 0:
        return 0.0
        
    return hits / total_users

def main():
    print("Starting Optimization...")
    
    # 1. Ensure Train Matrix exists
    if not os.path.exists('data/train.csv'):
        print("Error: data/train.csv not found. Run split_data.py first.")
        return

    # 2. Re-build Matrix on TRAIN only
    # We call building script via import
    import build_interaction_matrix
    print("Building Model from TRAIN SET...")
    build_interaction_matrix.build_matrix('data/train.csv') # Updates model_artifacts
    
    # 3. Load Model
    print("Loading Recommender...")
    rec = Recommender()
    
    # 4. Load Validation Data
    print("Loading Validation Set...")
    valid_df = pd.read_csv('data/valid.csv')
    
    # 5. Grid Search
    # We loop K first (expensive training), then Alpha (cheap inference)
    k_values = [50, 100, 200]
    alphas = [0.0, 0.5, 0.7, 1.0]
    
    best_score = -1
    best_params = {}
    
    print(f"\nEvaluating Parameters (K, Alpha)...")
    
    for k in k_values:
        print(f"\n--- Training with K={k} ---")
        # Retrain Model with K
        # Use sys.executable to ensure we use the same python interpreter
        cmd = f"{sys.executable} train_user_cf.py --neighbors {k}"
        ret = os.system(cmd)
        if ret != 0:
            print(f"Error training model with K={k}")
            continue
        
        # Reload Recommender to get new model
        rec = Recommender()
        
        for alpha in alphas:
            # Note: recommend() usually uses fixed K from model or defaults.
            # We must ensure recommend() respects the trained K.
            # user_cf.py uses self.model.kneighbors(..., n_neighbors=k)
            # If the model was trained with K=200, we can query up to 200.
            
            recall = evaluate_recall_at_k(rec, valid_df, k=10, alpha=alpha)
            print(f"K={k}, Alpha={alpha:.1f} | Recall@10: {recall:.4f}")
            
            if recall > best_score:
                best_score = recall
                best_params = {'k': k, 'alpha': alpha}
            
    print("\noptimization Complete.")
    print(f"Best Params: K={best_params['k']}, Alpha={best_params['alpha']} (Recall: {best_score:.4f})")
    
    # Save best? Or just report.
    # For now just report.

if __name__ == "__main__":
    main()
