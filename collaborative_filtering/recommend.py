import pickle
import scipy.sparse
import numpy as np
import os
import joblib
from user_cf import UserUserCF 

# Configuration
ARTIFACTS_DIR = 'model_artifacts'

class Recommender:
    def __init__(self):
        print("Loading artifacts...")
        # Load Mappings
        with open(os.path.join(ARTIFACTS_DIR, 'mappings.pkl'), 'rb') as f:
            mappings = pickle.load(f)
            self.user_to_idx = mappings['user_to_idx']
            self.item_to_idx = mappings['item_to_idx']
            self.idx_to_item = mappings['idx_to_item']
            self.idx_to_user = mappings['idx_to_user']
            self.item_to_category = mappings.get('item_to_category', {})
            
        # Load Sparse Matrix (for filtering valid items / popularity)
        self.user_item_matrix = scipy.sparse.load_npz(os.path.join(ARTIFACTS_DIR, 'user_item_matrix.npz'))
        
        # Initialize User-User CF
        try:
            self.user_cf = UserUserCF()
        except Exception as e:
            print(f"Warning: User-User CF artifacts not found or error loading: {e}")
            self.user_cf = None
        
    def recommend(self, user_id, top_k=10):
        """
        Main recommendation method. Uses User-User CF with Popularity Fallback.
        """
        if not self.user_cf:
            return [{"item_id": "Error", "score": 0, "source": "System", "reason": "Model Unavailable"}]

        # 1. Get CF Recommendations (Raw Scores favored)
        # We assume CF returns reasonable scores.
        cf_recs = self.user_cf.recommend(user_id, k=top_k * 2) # Get more candidates
        
        # Convert to Dictionary for easy lookup: item_id -> score
        # Normalize CF scores (simple max norm for now)
        cf_scores = {}
        cf_recs_map = {} # Map item_id -> rec object (for metadata)
        
        if cf_recs:
             max_cf = max(r.get('score', 0) for r in cf_recs) if cf_recs else 1.0
             if max_cf <= 0: max_cf = 1.0
             
             for r in cf_recs:
                 cf_scores[r['item_id']] = r.get('score', 0) / max_cf
                 cf_recs_map[r['item_id']] = r
                 
        # 2. Get Popularity Scores (Global)
        # We calculate this once or cache it, but for now calculate on fly is fast enough or use pre-calc
        # Let's get top items and their raw weights
        pop_candidates = self.get_popular_items_with_scores(top_k=500)
        
        # Normalize Pop scores
        pop_scores = {}
        if pop_candidates:
            max_pop = pop_candidates[0]['score']
            if max_pop <= 0: max_pop = 1.0
            for r in pop_candidates:
                pop_scores[r['item_id']] = r['score'] / max_pop
                
        # 3. Hybrid Merge
        # Score = alpha * CF + (1-alpha) * Pop
        ALPHA = 0.7 # 70% Personalization, 30% Popularity
        
        combined_candidates = set(cf_scores.keys()) | set(pop_scores.keys())
        
        # Get User Seen items to filter
        seen_items = set()
        if user_id in self.user_to_idx:
            user_idx = self.user_to_idx[user_id]
            # Get user profile for explanation
            user_profile = self.get_user_profile(user_idx)
        else:
            user_idx = None
            user_profile = {}
            
        final_recs = []
        for item_id in combined_candidates:
            if item_id in seen_items:
                continue
                
            s_cf = cf_scores.get(item_id, 0.0)
            s_pop = pop_scores.get(item_id, 0.0)
            
            final_score = (ALPHA * s_cf) + ((1 - ALPHA) * s_pop)
            
            # Source
            if s_cf > 0 and s_pop > 0: source = "Hybrid"
            elif s_cf > 0: source = "Personalized"
            else: source = "Popularity"
            
            # Get Metadata from CF Recs if available
            neighbor_count = 0
            similar_users = []
            if item_id in cf_recs_map:
                neighbor_count = cf_recs_map[item_id].get('neighbor_count', 0)
                similar_users = cf_recs_map[item_id].get('similar_users', [])

            # Explanation
            reason = self.explain_recommendation(item_id, source, user_profile, neighbor_count, similar_users)
            
            final_recs.append({
                'item_id': item_id,
                'score': final_score,
                'source': source,
                'reason': reason,
                'neighbor_count': neighbor_count,
                'similar_users': similar_users
            })
            
        # Sort by Final Score
        final_recs.sort(key=lambda x: x['score'], reverse=True)
        
        return final_recs[:top_k]

    def get_user_profile(self, user_idx):
        """
        Builds a simple profile of category interests for explanation.
        """
        if user_idx is None:
            return {}
            
        # Get interacted items
        indices = self.user_item_matrix[user_idx].indices
        data = self.user_item_matrix[user_idx].data
        
        profile = {}
        for idx, weight in zip(indices, data):
            item_id = self.idx_to_item.get(idx)
            category = self.item_to_category.get(item_id, "Unknown")
            
            if category:
                profile[category] = profile.get(category, 0) + weight
                
        # Normalize/Sort
        return profile

    def explain_recommendation(self, item_id, source, user_profile, neighbor_count=0, similar_users=None):
        """
        Generates a text explanation for the recommendation.
        """
        category = self.item_to_category.get(item_id, "Unknown")
        
        if source == "Popularity":
            if category != "Unknown":
                return f"Trending in {category}"
            else:
                return "Trending item"
                
        # For Personalized / Hybrid
        
        # Priority 1: User-Centric (Neighbor Count + Who + Action)
        if neighbor_count > 0:
            
            # Format "Who"
            if similar_users:
                # similar_users is now a list of dicts: [{'id': '...', 'weight': 5.0}]
                # OR list of strings (backward compatibility check)
                
                details = []
                for u in similar_users:
                    if isinstance(u, dict):
                        uid = u['id']
                        w = u['weight']
                        
                        # Infer Action
                        if w >= 5.0: action = "Bought"
                        elif w >= 3.0: action = "Added to Cart"
                        elif w >= 2.0: action = "Liked"
                        else: action = "Viewed"
                        
                        details.append(f"{uid} ({action})")
                    else:
                        details.append(str(u)) # Fallback
                    
                who_str = ", ".join(details)
                return f"Activty by {who_str}"
            else:
                user_text = "users" if neighbor_count > 1 else "user"
                return f"Liked by {neighbor_count} similar {user_text}"
            
        # Priority 2: Category Affinity (Fallback)
        if category in user_profile:
            return f"Because you view {category}"
            
        # Fallback explanation
        return "Popular with users similar to you"

    def get_popular_items(self, top_k=5000):
        # Calculate popularity based on total weight (column sum of user_item_matrix)
        item_frequencies = self.user_item_matrix.sum(axis=0).A1 
        
        # Get indices of top_k items
        top_indices = np.argsort(item_frequencies)[-top_k:][::-1]
        
        popular_items = []
        for idx in top_indices:
            item_id = self.idx_to_item.get(idx, None)
            if item_id:
                popular_items.append(item_id)
                
        return popular_items

    def get_popular_items_with_scores(self, top_k=5000):
        # Calculate popularity based on total weight (column sum of user_item_matrix)
        item_frequencies = self.user_item_matrix.sum(axis=0).A1 
        
        # Get indices of top_k items
        top_indices = np.argsort(item_frequencies)[-top_k:][::-1]
        
        candidates = []
        for idx in top_indices:
            item_id = self.idx_to_item.get(idx, None)
            score = item_frequencies[idx]
            if item_id:
                candidates.append({
                    'item_id': item_id,
                    'score': float(score)
                })
                
        return candidates

if __name__ == "__main__":
    rec = Recommender()
    pass
