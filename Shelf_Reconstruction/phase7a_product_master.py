"""
Phase 7A: Product Master Creation
=================================
This script acts as the prototype dataset builder. It generates
product_master.csv containing the metadata for the 10 SKUs in
our GroceryDataset. Downstream components should read this file.

Usage:
    python Shelf_Reconstruction/phase7a_product_master.py
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "Dataset"

BRAND_MAP = {
    1: "Marlboro",
    2: "Kent",
    3: "LM",
    4: "Parliament",
    5: "Pall Mall",
    6: "Camel",
    7: "Winston",
    8: "Lucky Strike",
    9: "Muratti",
    10: "Tekel"
}

def create_product_master():
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATASET_DIR / "product_master.csv"
    
    data = []
    for cat_id, brand in BRAND_MAP.items():
        sku_id = f"SKU_{cat_id:03d}"
        data.append({
            "sku_id": sku_id,
            "product_name": brand,
            "brand": brand,
            "category": "Cigarette"
        })
        
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    
    print(f"✅ Generated Product Master at {csv_path}")
    print(df.head(10))

if __name__ == "__main__":
    create_product_master()
