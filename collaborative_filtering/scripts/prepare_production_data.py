import pandas as pd
import os
import argparse

def prepare_data(input_file, output_file, min_interactions=5):
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
    
    # Filter Items (>= 3 interactions)
    item_counts = df['item_id'].value_counts()
    valid_items = item_counts[item_counts >= 3].index
    df = df[df['item_id'].isin(valid_items)]
    print(f"After Item Filter (>=3): {df.shape} (Items: {len(valid_items)})")
    
    # 2. Saving
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    df.to_csv(output_file, index=False)
    print(f"Saved production data to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, default='enriched_logs.csv', help='Input CSV file')
    parser.add_argument('--output', type=str, default='data/production.csv', help='Output CSV file')
    parser.add_argument('--min-interactions', type=int, default=5, help='Minimum interactions per user')
    args = parser.parse_args()
    
    prepare_data(args.input, args.output, min_interactions=args.min_interactions)
