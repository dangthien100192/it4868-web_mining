
import scipy.sparse as sparse
from sklearn.preprocessing import normalize
import os
import argparse

# Configuration
ARTIFACTS_DIR = 'model_artifacts'
INPUT_MATRIX = 'user_item_matrix.npz'
OUTPUT_MATRIX = 'user_norm_matrix.npz'

def prep_user_data():
    input_path = os.path.join(ARTIFACTS_DIR, INPUT_MATRIX)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input matrix not found at {input_path}. Please run prep_data.py first.")

    print(f"Loading user-item matrix from {input_path}...")
    user_item_matrix = sparse.load_npz(input_path)
    
    print(f"Matrix shape: {user_item_matrix.shape}")
    
    # L2 Normalization along axis 1 (rows/users)
    # This ensures that the dot product of two vectors is equivalent to Cosine Similarity
    print("Applying L2 normalization to user vectors...")
    user_norm_matrix = normalize(user_item_matrix, norm='l2', axis=1)
    
    output_path = os.path.join(ARTIFACTS_DIR, OUTPUT_MATRIX)
    print(f"Saving normalized matrix to {output_path}...")
    sparse.save_npz(output_path, user_norm_matrix)
    
    print("User data preparation complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare normalized user data for User-User CF")
    args = parser.parse_args()
    
    prep_user_data()
