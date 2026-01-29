"""
Product Recommender Module
Implements TF-IDF based product similarity recommendation system
"""

import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import hstack


class ProductRecommender:
    def __init__(self, property_weights=None):
        """
        Initialize ProductRecommender
        
        Args:
            property_weights: dict - weight cho từng property_id
                              Ví dụ: {"1": 2.0, "9": 1.5, "23": 0.5}
        """
        self.property_weights = property_weights or {}
        self.vectorizers = {}
        self.property_vectors = {}
        self.product_ids = []
        self.similarity_matrix = None
        self.products_data = None
        
    def load_products(self, products_data):
        """
        Load dữ liệu products từ list of JSON objects
        
        Args:
            products_data: list of dict - danh sách products
        """
        self.products_data = products_data
        self.product_ids = [p['product_id'] for p in products_data]
        
    def _extract_property_corpus(self):
        """
        Bước 1: Extract property values cho từng product
        
        Returns:
            property_corpus: dict - {property_id: [text_product_1, text_product_2, ...]}
        """
        # Bước 1: Tìm tất cả property_ids có trong dataset
        all_property_ids = set()
        for product in self.products_data:
            for prop in product.get('product_properties', []):
                all_property_ids.add(prop['product_property_id'])
        
        # Bước 2: Khởi tạo corpus với empty strings cho tất cả properties
        property_corpus = {prop_id: [] for prop_id in all_property_ids}
        
        # Bước 3: Duyệt qua từng product và fill values
        for product in self.products_data:
            # Tạo dict để lưu property của product này
            product_properties = {}
            
            # Extract từng property
            for prop in product.get('product_properties', []):
                property_id = prop['product_property_id']
                
                # Ghép tất cả property_values thành 1 string
                values = [pv['property_value'] for pv in prop.get('property_values', [])]
                combined_text = ' '.join(values)
                
                product_properties[property_id] = combined_text
            
            # Thêm vào corpus (đảm bảo tất cả properties đều có giá trị)
            for property_id in all_property_ids:
                text = product_properties.get(property_id, '')  # Empty string nếu không có
                property_corpus[property_id].append(text)
        
        return property_corpus
    
    def fit(self, max_features=100):
        """
        Bước 2 & 3: Vectorize từng property riêng và ghép lại
        
        Args:
            max_features: số features tối đa cho mỗi TF-IDF vectorizer
        """
        # Extract property corpus
        property_corpus = self._extract_property_corpus()
        
        print(f"Tìm thấy {len(property_corpus)} properties khác nhau")
        print(f"Số lượng products: {len(self.products_data)}")
        
        # Validate: tất cả properties phải có cùng số lượng texts
        for property_id, texts in property_corpus.items():
            if len(texts) != len(self.products_data):
                raise ValueError(
                    f"Property {property_id} có {len(texts)} texts "
                    f"nhưng có {len(self.products_data)} products!"
                )
        
        # Vectorize từng property riêng
        property_vectors_list = []
        
        for property_id, texts in property_corpus.items():
            print(f"Vectorizing property_id: {property_id} ({len(texts)} products)")
            
            # Tạo TF-IDF vectorizer riêng cho property này
            vectorizer = TfidfVectorizer(
                max_features=max_features,
                ngram_range=(1, 2),  # unigram + bigram
                min_df=1,  # xuất hiện ít nhất 1 lần
                lowercase=True
            )
            
            # Fit và transform
            vectors = vectorizer.fit_transform(texts)
            
            # Lưu vectorizer để dùng sau
            self.vectorizers[property_id] = vectorizer
            
            # Apply weight nếu có
            weight = self.property_weights.get(property_id, 1.0)
            weighted_vectors = vectors * weight
            
            # Lưu vector
            self.property_vectors[property_id] = weighted_vectors
            property_vectors_list.append(weighted_vectors)
            
            print(f"  → Shape: {vectors.shape}, Weight: {weight}")
        
        # Ghép tất cả property vectors thành 1 vector cho mỗi product
        print("\nGhép tất cả property vectors...")
        self.combined_vectors = hstack(property_vectors_list)
        print(f"Final vector shape: {self.combined_vectors.shape}")

        
    def compute_similarity(self):
        """
        Bước 4: Tính similarity matrix
        """
        print("\nTính similarity matrix...")
        self.similarity_matrix = cosine_similarity(self.combined_vectors)
        print(f"Similarity matrix shape: {self.similarity_matrix.shape}")
        
    def get_recommendations(self, product_id, top_k=5, exclude_self=True):
        """
        Bước 5: Lấy top-K recommendations cho 1 product
        
        Args:
            product_id: ID của product cần recommend
            top_k: số lượng recommendations
            exclude_self: có loại bỏ chính product đó không
            
        Returns:
            list of tuples: [(product_id, similarity_score), ...]
        """
        if product_id not in self.product_ids:
            raise ValueError(f"Product {product_id} không tồn tại trong dataset")
        
        # Lấy index của product
        idx = self.product_ids.index(product_id)
        
        # Lấy similarity scores với tất cả products khác
        sim_scores = self.similarity_matrix[idx]
        
        # Tạo list (index, score)
        scores_with_idx = [(i, score) for i, score in enumerate(sim_scores)]
        
        # Sort theo score giảm dần
        scores_with_idx.sort(key=lambda x: x[1], reverse=True)
        
        # Lấy top-K (exclude self nếu cần)
        recommendations = []
        for i, score in scores_with_idx:
            if exclude_self and i == idx:
                continue
            recommendations.append((self.product_ids[i], score))
            if len(recommendations) >= top_k:
                break
        
        return recommendations
    
    def explain_similarity(self, product_id_1, product_id_2):
        """
        Giải thích tại sao 2 products giống nhau (theo từng property)
        
        Args:
            product_id_1, product_id_2: IDs của 2 products
            
        Returns:
            dict: {property_id: similarity_score}
        """
        idx1 = self.product_ids.index(product_id_1)
        idx2 = self.product_ids.index(product_id_2)
        
        explanations = {}
        
        for property_id, vectors in self.property_vectors.items():
            vec1 = vectors[idx1].reshape(1, -1)
            vec2 = vectors[idx2].reshape(1, -1)
            
            sim = cosine_similarity(vec1, vec2)[0][0]
            explanations[property_id] = sim
        
        return explanations
