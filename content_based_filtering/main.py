from recommender import ProductRecommender
from data_loader import load_products_from_json, load_sample_products, get_product_name
from utils import print_section, print_divider, print_recommendations


# ========== MAIN USAGE ==========

if __name__ == "__main__":
    
    # Load products from JSON file
    try:
        products = load_products_from_json("products.json")
    except FileNotFoundError:
        print("products.json not found, using sample data...")
        products = load_sample_products()
    
    # Khởi tạo recommender với weights
    property_weights = {
        "1": 2.0,   # Chipset quan trọng nhất
        "9": 1.5,   # Màn hình
        "23": 1.0   # Thông tin khác
    }
    
    recommender = ProductRecommender(property_weights=property_weights)
    
    # Load data
    print_section("LOADING PRODUCTS...")
    recommender.load_products(products)
    print(f"Loaded {len(products)} products")
    
    # Fit (vectorize)
    print_section("VECTORIZING...")
    recommender.fit(max_features=50)
    
    # Compute similarity
    print_section("COMPUTING SIMILARITY...")
    recommender.compute_similarity()
    
    # Get recommendations
    print_section("RECOMMENDATIONS")
    
    # Get first product ID for testing
    test_product_id = products[0]['product_id']
    
    recommendations = recommender.get_recommendations(test_product_id, top_k=5)
    print_recommendations(recommendations, products, test_product_id)