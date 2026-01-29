import pandas as pd
import scipy.sparse as sparse
import numpy as np
import pickle
import os
import argparse

# Configuration
INPUT_FILE = 'formatted_logs.csv'
ARTIFACTS_DIR = 'model_artifacts'
OUTPUT_MATRIX = 'user_item_matrix.npz'
OUTPUT_MAPPINGS = 'mappings.pkl'

# Interaction Weights (Implicit Feedback)
WEIGHTS_STANDARD = {
    'view_page': 1.0,
    'view_product': 1.0,
    'view_news': 0.5,
    'search': 1.5,
    'cart_interaction': 3.0,
    'checkout_interaction': 5.0,
    'like': 2.0,
    'rate_product': 2.0,
    'comment': 2.0
}

WEIGHTS_STEEP = {
    'view_page': 1.0,
    'view_product': 1.0,
    'view_news': 0.5,
    'search': 1.5,
    'cart_interaction': 10.0, # Steep increase
    'checkout_interaction': 20.0, # Massive intent
    'like': 5.0,
    'rate_product': 5.0,
    'comment': 5.0
}

WEIGHTS_FLAT = {
    'view_page': 1.0,
    'view_product': 1.0,
    'view_news': 1.0,
    'search': 1.0,
    'cart_interaction': 1.0,
    'checkout_interaction': 1.0,
    'like': 1.0,
    'rate_product': 1.0,
    'comment': 1.0
}

def build_matrix(input_file=INPUT_FILE, weight_profile='standard'):
    print(f"Loading data from {input_file}...")
    if not os.path.exists(input_file):
        # Fallback to enriched if formatted not found, just in case
        if os.path.exists('enriched_logs.csv'):
            print("formatted_logs.csv not found, using enriched_logs.csv...")
            input_file = 'enriched_logs.csv'
        else:
             raise FileNotFoundError(f"{input_file} not found. Run process_logs.py first.")

    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows.")
    
    # Create Mappings
    print("Creating User/Item Mappings...")
    user_ids = df['user_id'].dropna().unique()
    item_ids = df['item_id'].dropna().unique()
    
    user_to_idx = {uid: i for i, uid in enumerate(user_ids)}
    idx_to_user = {i: uid for i, uid in enumerate(user_ids)}
    
    item_to_idx = {iid: i for i, iid in enumerate(item_ids)}
    idx_to_item = {i: iid for i, iid in enumerate(item_ids)}
    
    print(f"Users: {len(user_ids)}, Items: {len(item_ids)}")
    
    # Calculate Weights
    print(f"Calculating Interaction Weights ({weight_profile.upper()})...")
    
    if weight_profile.lower() == 'steep':
        chosen_weights = WEIGHTS_STEEP
    elif weight_profile.lower() == 'flat':
        chosen_weights = WEIGHTS_FLAT
    else:
        chosen_weights = WEIGHTS_STANDARD
        
    # Map action to weight
    df['weight'] = df['action'].map(chosen_weights).fillna(1.0)
    
    # --- Time Decay Logic ---
    print("Applying Time Decay...")
    if 'timestamp' in df.columns:
        # Convert to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Reference date (max date in data or now)
        max_date = df['timestamp'].max()
        if pd.isnull(max_date):
            max_date = pd.Timestamp.now()
            
        print(f"Ref Date for Decay: {max_date}")
        
        # Calculate days diff
        DECAY_RATE = 0.02
        
        df['days_diff'] = (max_date - df['timestamp']).dt.days.fillna(0)
        df['days_diff'] = df['days_diff'].clip(lower=0) 
        
        df['decay'] = np.exp(-DECAY_RATE * df['days_diff'])
        
        # Apply decay
        df['weight'] = df['weight'] * df['decay']
    else:
        print("Warning: 'timestamp' column not found. Skipping Time Decay.")
    
    # Group by User-Item and Sum weights
    interactions = df.groupby(['user_id', 'item_id'])['weight'].sum().reset_index()
    
    # Create Sparse Matrix
    print("Building Sparse Matrix...")
    row_indices = interactions['user_id'].map(user_to_idx).values
    col_indices = interactions['item_id'].map(item_to_idx).values
    data = interactions['weight'].values
    
    matrix = sparse.csr_matrix((data, (row_indices, col_indices)), shape=(len(user_ids), len(item_ids)))
    
    # Save Artifacts
    if not os.path.exists(ARTIFACTS_DIR):
        os.makedirs(ARTIFACTS_DIR)
        
    print(f"Saving Matrix to {os.path.join(ARTIFACTS_DIR, OUTPUT_MATRIX)}...")
    sparse.save_npz(os.path.join(ARTIFACTS_DIR, OUTPUT_MATRIX), matrix)
    
    mappings = {
        'user_to_idx': user_to_idx,
        'idx_to_user': idx_to_user,
        'item_to_idx': item_to_idx,
        'idx_to_item': idx_to_item,
        'item_to_category': df.set_index('item_id')['category'].to_dict()
    }
    
    print(f"Saving Mappings to {os.path.join(ARTIFACTS_DIR, OUTPUT_MAPPINGS)}...")
    with open(os.path.join(ARTIFACTS_DIR, OUTPUT_MAPPINGS), 'wb') as f:
        pickle.dump(mappings, f)
        
    print("Build complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, default=INPUT_FILE, help='Path to input CSV')
    parser.add_argument('--weight-profile', type=str, default='standard', choices=['standard', 'steep', 'flat'], help='Weight profile to use')
    args = parser.parse_args()
    
    build_matrix(args.input, weight_profile=args.weight_profile)
