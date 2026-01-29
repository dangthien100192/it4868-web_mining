"""
Utilities Module
Helper functions for display and formatting
"""


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_divider(char="-", width=60):
    """Print a divider line"""
    print(char * width)


def print_recommendations(recommendations, products, test_product_id):
    """
    Print recommendations in a formatted way
    
    Args:
        recommendations: list of (product_id, score) tuples
        products: list of product dicts
        test_product_id: ID of the product being recommended for
    """
    print(f"\nTop {len(recommendations)} sản phẩm tương tự với '{test_product_id}':")
    print_divider()
    
    for rank, (pid, score) in enumerate(recommendations, 1):
        product_name = next(
            (p['product_name'] for p in products if p['product_id'] == pid),
            "Unknown"
        )
        print(f"{rank}. Product ID: {pid}")
        print(f"   Name: {product_name}")
        print(f"   Similarity Score: {score:.4f}")
        print()


def print_similarity_explanation(explanation, property_id_map=None):
    """
    Print similarity explanation
    
    Args:
        explanation: dict of {property_id: similarity_score}
        property_id_map: optional dict mapping property_id to property name
    """
    print("\nSimilarity Breakdown by Property:")
    print_divider()
    
    for prop_id, sim_score in sorted(explanation.items(), key=lambda x: x[1], reverse=True):
        prop_name = property_id_map.get(prop_id, f"Property {prop_id}") if property_id_map else f"Property {prop_id}"
        print(f"{prop_name}: {sim_score:.4f}")
