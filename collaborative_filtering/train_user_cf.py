
import os
import pickle
import argparse
import scipy.sparse as sparse
from sklearn.neighbors import NearestNeighbors
import joblib

# Configuration
ARTIFACTS_DIR = 'model_artifacts'
INPUT_MATRIX = 'user_norm_matrix.npz'
OUTPUT_MODEL = 'user_nn_model.pkl'

def train_user_model(n_neighbors=50, metric='cosine'):
    input_path = os.path.join(ARTIFACTS_DIR, INPUT_MATRIX)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input matrix not found at {input_path}. Please run prep_user_data.py first.")
    
    print(f"Loading user matrix from {input_path}...")
    user_matrix = sparse.load_npz(input_path)
    
    print(f"User Matrix Shape: {user_matrix.shape}")
    
    # 2. Train NearestNeighbors
    # Metric: cosine distance is standard for CF
    print(f"Initializing NearestNeighbors (k={n_neighbors}, metric=cosine)...")
    model = NearestNeighbors(n_neighbors=n_neighbors, algorithm='brute', metric='cosine')
    
    print("Fitting model (indexing)...")
    model.fit(user_matrix)
    
    # 3. Save Model
    output_path = os.path.join(ARTIFACTS_DIR, OUTPUT_MODEL)
    print(f"Saving model to {output_path}...")
    joblib.dump(model, output_path)
    
    print("Training complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--neighbors', type=int, default=50, help='Number of neighbors (K)')
    args = parser.parse_args()
    
    train_user_model(n_neighbors=args.neighbors)
