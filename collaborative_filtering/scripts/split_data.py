import pandas as pd
import numpy as np
import os
import argparse

def split_data(input_file, train_ratio=0.8, valid_ratio=0.1, output_dir='data', min_interactions=5):
    print(f"Loading {input_file}...")
    df = pd.read_csv(input_file)
    
    # 1. Filtering
    print("Filtering Data...")
    print(f"Original shape: {df.shape}")
    
    # Filter Users
    user_counts = df['user_id'].value_counts()
    valid_users = user_counts[user_counts >= min_interactions].index
    df = df[df['user_id'].isin(valid_users)]
    print(f"After User Filter (>={min_interactions}): {df.shape} (Users: {len(valid_users)})")
    
    # Filter Items (Keep fixed at 3 for now, or make arg)
    item_counts = df['item_id'].value_counts()
    valid_items = item_counts[item_counts >= 3].index
    df = df[df['item_id'].isin(valid_items)]
    print(f"After Item Filter (>=3): {df.shape} (Items: {len(valid_items)})")
    
    # 2. Sorting by Time
    if 'timestamp' in df.columns:
        print("Parsing timestamps...")
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce', utc=True)
        df = df.dropna(subset=['timestamp']) # Drop rows with invalid dates
        df = df.sort_values('timestamp')
    else:
        print("Warning: No timestamp column found. Splitting sequentially (assuming pre-sorted).")
        
    # 3. Splitting
    n = len(df)
    train_end = int(n * train_ratio)
    valid_end = int(n * (train_ratio + valid_ratio))
    
    train = df.iloc[:train_end]
    valid = df.iloc[train_end:valid_end]
    test = df.iloc[valid_end:]
    
    print(f"Split Results:")
    print(f"Train: {len(train)}")
    print(f"Valid: {len(valid)}")
    print(f"Test: {len(test)}")
    
    # 4. Saving
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    train.to_csv(os.path.join(output_dir, 'train.csv'), index=False)
    valid.to_csv(os.path.join(output_dir, 'valid.csv'), index=False)
    test.to_csv(os.path.join(output_dir, 'test.csv'), index=False)
    print(f"Saved splits to {output_dir}/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, default='enriched_logs.csv', help='Input CSV file')
    parser.add_argument('--min-interactions', type=int, default=5, help='Minimum interactions per user')
    args = parser.parse_args()
    
    split_data(args.input, min_interactions=args.min_interactions)
