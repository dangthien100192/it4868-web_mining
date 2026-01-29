
import os
import pickle
import joblib
import numpy as np
import scipy.sparse as sparse

class UserUserCF:
    def __init__(self, artifacts_dir='model_artifacts'):
        self.artifacts_dir = artifacts_dir
        self.mappings = None
        self.user_norm_matrix = None
        self.user_raw_matrix = None
        self.model = None
        self.load_artifacts()

    def load_artifacts(self):
        print("Loading User-User CF artifacts...")
        
        # Mappings
        with open(os.path.join(self.artifacts_dir, 'mappings.pkl'), 'rb') as f:
            self.mappings = pickle.load(f)
            self.user_to_idx = self.mappings['user_to_idx']
            self.idx_to_user = self.mappings['idx_to_user']
            self.item_to_idx = self.mappings['item_to_idx']
            self.idx_to_item = self.mappings['idx_to_item']
            
        # Matrices
        self.user_norm_matrix = sparse.load_npz(os.path.join(self.artifacts_dir, 'user_norm_matrix.npz'))
        self.user_raw_matrix = sparse.load_npz(os.path.join(self.artifacts_dir, 'user_item_matrix.npz'))
        
        # Model
        self.model = joblib.load(os.path.join(self.artifacts_dir, 'user_nn_model.pkl'))
        print("Artifacts loaded.")

    def recommend_from_vector(self, query_vec, interacted_indices=None, k=10, n_neighbors=50):
        """
        Recommend items based on a sparse interaction vector (1, N_items).
        """
        # 3. Find Neighbors
        distances, indices = self.model.kneighbors(query_vec, n_neighbors=n_neighbors)
        
        distances = distances.flatten()
        neighbor_indices = indices.flatten()
        
        # 4. Compute Similarities
        similarities = 1.0 - distances
        
        if len(similarities) == 0:
            return []

        # 5. Score Items
        neighbor_ratings = self.user_raw_matrix[neighbor_indices] # Shape (K, M)
        sim_vector = sparse.csr_matrix(similarities)
        scores = sim_vector.dot(neighbor_ratings)
        scores_dense = scores.toarray().flatten()
        
        # 6. Filter Interacted Items
        if interacted_indices is not None and len(interacted_indices) > 0:
            scores_dense[interacted_indices] = -np.inf
        
        # 7. Rank and Top-K
        if k >= len(scores_dense):
            top_indices = np.argsort(scores_dense)[::-1]
        else:
            top_indices = np.argpartition(scores_dense, -k)[-k:]
            top_indices = top_indices[np.argsort(scores_dense[top_indices])[::-1]]
            
        recommendations = []
        recommendations = []
        for idx in top_indices:
            score = scores_dense[idx]
            if score <= 0: continue
            
            item_id = self.idx_to_item.get(idx, "Unknown")
            
            # Calculate Neighbor Count (How many similar users liked this?)
            # Get the column for this item from neighbor_ratings
            # neighbor_ratings is (n_neighbors, n_items)
            item_col = neighbor_ratings[:, idx]
            neighbor_count = item_col.getnnz()
            
            # Who are they?
            sim_users = []
            if neighbor_count > 0:
                # Get indices of neighbors who liked it (non-zero entries in column)
                row_indices = item_col.nonzero()[0]
                
                # These are indices relative to the 'neighbor_indices' list
                # We need to map back to global User Indices then User IDs
                
                # neighbor_indices is global list of K neighbors
                # row_indices is local index within K
                
                for local_idx in row_indices:
                     global_user_idx = neighbor_indices[local_idx]
                     u_id = self.idx_to_user.get(global_user_idx, "Unknown")
                     
                     # Get the weight of this interaction
                     # item_col is a sparse column vector (1, N_neighbors) if transposed or (N_neighbors, 1)
                     # Actually neighbor_ratings is (N_neighbors, N_items), so item_col is (N_neighbors, 1)
                     # local_idx is the row index in item_col
                     weight = item_col[local_idx, 0] 
                     
                     sim_users.append({
                         'id': u_id,
                         'weight': float(weight)
                     })
                     
                     if len(sim_users) >= 3: 
                         break
            
            recommendations.append({
                'item_id': item_id,
                'score': float(score),
                'source': 'UserUserCF',
                'neighbor_count': int(neighbor_count),
                'similar_users': sim_users
            })
            
        return recommendations

    def recommend(self, user_id, k=10, n_neighbors=50):
        """
        Recommend items for a given user_id using User-User CF.
        """
        # 1. Check if user exists
        if user_id not in self.user_to_idx:
            print(f"User {user_id} not found in training data.")
            return [] 
            
        user_idx = self.user_to_idx[user_id]
        
        # 2. Get User Vector (Normalized)
        query_vec = self.user_norm_matrix[user_idx]
        
        # Get interacted items to filter
        interacted_indices = self.user_raw_matrix[user_idx].indices
        
        return self.recommend_from_vector(query_vec, interacted_indices=interacted_indices, k=k, n_neighbors=n_neighbors)

if __name__ == "__main__":
    # Simple test
    cf = UserUserCF()
    # Test with a known user (get one from mappings)
    test_user = list(cf.user_to_idx.keys())[0]
    print(f"Testing recommendations for user: {test_user}")
    recs = cf.recommend(test_user, k=5)
    print("Top 5 Recommendations:")
    for r in recs:
        print(r)
