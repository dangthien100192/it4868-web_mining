"""
Data Loader Module
Handles loading and processing product data
"""

import json


def load_products_from_json(file_path):
    """
    Load products from JSON file
    
    Args:
        file_path: path to JSON file
        
    Returns:
        list: list of product dictionaries
    """
    with open(file_path, "r", encoding="utf-8") as file:
        products = json.load(file)
    return products


def load_sample_products():
    """
    Return sample product data for testing
    
    Returns:
        list: sample products
    """
    return [
        {
            "product_id": "1010016101339",
            "product_name": "Samsung Galaxy J3 Pro Blue Silver",
            "product_properties": [
                {
                    "product_property_id": "9",
                    "product_property": "Màn hình",
                    "property_values": [
                        {"property_value": "5\" PLS TFT LCD HD (720 x 1280 pixels)"}
                    ]
                },
                {
                    "product_property_id": "1",
                    "product_property": "Chipset",
                    "property_values": [
                        {"property_value": "Exynos 7570 4 nhân 64-bit"}
                    ]
                },
                {
                    "product_property_id": "23",
                    "product_property": "Thông tin khác",
                    "property_values": [
                        {"property_value": "Camera Tự động lấy nét, HDR, Panorama"}
                    ]
                }
            ]
        },
        {
            "product_id": "1010016101340",
            "product_name": "Samsung Galaxy J5 Pro",
            "product_properties": [
                {
                    "product_property_id": "9",
                    "product_property": "Màn hình",
                    "property_values": [
                        {"property_value": "5.2\" Super AMOLED Full HD"}
                    ]
                },
                {
                    "product_property_id": "1",
                    "product_property": "Chipset",
                    "property_values": [
                        {"property_value": "Exynos 7870 8 nhân"}
                    ]
                },
                {
                    "product_property_id": "23",
                    "product_property": "Thông tin khác",
                    "property_values": [
                        {"property_value": "Camera 13MP, HDR, Flash LED"}
                    ]
                }
            ]
        },
        {
            "product_id": "1010016101341",
            "product_name": "iPhone 8 Plus",
            "product_properties": [
                {
                    "product_property_id": "9",
                    "product_property": "Màn hình",
                    "property_values": [
                        {"property_value": "5.5\" Retina HD IPS LCD"}
                    ]
                },
                {
                    "product_property_id": "1",
                    "product_property": "Chipset",
                    "property_values": [
                        {"property_value": "Apple A11 Bionic 6 nhân"}
                    ]
                },
                {
                    "product_property_id": "23",
                    "product_property": "Thông tin khác",
                    "property_values": [
                        {"property_value": "Camera kép 12MP, Portrait mode"}
                    ]
                }
            ]
        },
        {
            "product_id": "1010016101342",
            "product_name": "Samsung Galaxy Note 8",
            "product_properties": [
                {
                    "product_property_id": "9",
                    "product_property": "Màn hình",
                    "property_values": [
                        {"property_value": "6.3\" Super AMOLED QHD+"}
                    ]
                },
                {
                    "product_property_id": "1",
                    "product_property": "Chipset",
                    "property_values": [
                        {"property_value": "Exynos 8895 8 nhân"}
                    ]
                },
                {
                    "product_property_id": "23",
                    "product_property": "Thông tin khác",
                    "property_values": [
                        {"property_value": "Camera kép, S Pen, HDR"}
                    ]
                }
            ]
        }
    ]


def get_product_name(product_id, products):
    """
    Get product name by ID
    
    Args:
        product_id: ID of product
        products: list of products
        
    Returns:
        str: product name or "Unknown" if not found
    """
    for p in products:
        if p['product_id'] == product_id:
            return p['product_name']
    return "Unknown"
