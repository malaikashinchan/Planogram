"""
Phase 7B: Ideal Planogram Dataset Creation
==========================================
Generates Project-defined prototype ideal planograms in 4 formats:
JSON, CSV, XLS, and XLSX. 

These serve as controlled ground truth to test the comparison engine 
against our test shelf crops, since GroceryDataset does not provide 
ideal planograms.

Usage:
    python Shelf_Reconstruction/phase7b_ideal_planograms.py
"""

import pandas as pd
import json
from pathlib import Path
import os
import xlwt

BASE_DIR = Path(__file__).parent.parent
IDEAL_DIR = BASE_DIR / "Dataset" / "ideal_planograms"

def create_directories():
    for folder in ['json', 'csv', 'xls', 'xlsx', 'canonical']:
        (IDEAL_DIR / folder).mkdir(parents=True, exist_ok=True)

def generate_mock_planogram_data(pid: str):
    """
    Generates a unique mock planogram based on the ID.
    Returns a list of dictionary rows representing the flat table structure.
    """
    layouts = {
        "P001": [
            (1, 1, "SKU_001"), (1, 2, "SKU_001"), (1, 3, "SKU_002"), (1, 4, "SKU_004"),
            (2, 1, "SKU_003"), (2, 2, "SKU_003"), (2, 3, "SKU_007"), (2, 4, "SKU_008")
        ],
        "P002": [
            (1, 1, "SKU_005"), (1, 2, "SKU_005"), (1, 3, "SKU_005"), (1, 4, "SKU_005"),
            (2, 1, "SKU_006"), (2, 2, "SKU_006"), (2, 3, "SKU_006")
        ],
        "P003": [
            (1, 1, "SKU_009"), (1, 2, "SKU_010"), (1, 3, "SKU_009"), (1, 4, "SKU_010"),
            (2, 1, "SKU_001"), (2, 2, "SKU_002"), (2, 3, "SKU_003"), (2, 4, "SKU_004"),
            (3, 1, "SKU_005"), (3, 2, "SKU_006"), (3, 3, "SKU_007")
        ],
        "P004": [
            (1, 1, "SKU_001"), (1, 2, "SKU_002"), (1, 3, "SKU_001"), (1, 4, "SKU_002")
        ],
        "P005": [
            (1, 1, "SKU_007"), (1, 2, "SKU_008"), (1, 3, "SKU_009"),
            (2, 1, "SKU_007"), (2, 2, "SKU_008"), (2, 3, "SKU_009"),
            (3, 1, "SKU_007"), (3, 2, "SKU_008"), (3, 3, "SKU_009")
        ]
    }
    
    # If the ID is not in our manual layouts, use a fixed safe default
    layout = layouts.get(pid, [
        (1, 1, "SKU_001"), (1, 2, "SKU_002"), 
        (2, 1, "SKU_003"), (2, 2, "SKU_004")
    ])
    
    data = []
    for shelf_id, position, sku_id in layout:
        data.append({
            "planogram_id": pid, 
            "version": 1, 
            "store_id": "STORE_001", 
            "shelf_id": shelf_id, 
            "position": position, 
            "sku_id": sku_id
        })
    return data

def write_json(data):
    # JSON structure is hierarchical natively
    planogram_id = data[0]["planogram_id"]
    
    planogram = {
        "planogram_id": planogram_id,
        "version": 1,
        "store_id": "STORE_001",
        "shelves": []
    }
    
    shelves = {}
    for row in data:
        sid = row["shelf_id"]
        if sid not in shelves:
            shelves[sid] = {"shelf_id": sid, "products": []}
        shelves[sid]["products"].append({
            "position": row["position"],
            "sku_id": row["sku_id"]
        })
        
    planogram["shelves"] = [shelves[k] for k in sorted(shelves.keys())]
    
    path = IDEAL_DIR / "json" / f"{data[0]['planogram_id']}.json"
    with open(path, 'w') as f:
        json.dump(planogram, f, indent=2)
    print(f"✅ Created {path}")

def write_csv(data):
    df = pd.DataFrame(data)
    path = IDEAL_DIR / "csv" / f"{data[0]['planogram_id']}.csv"
    df.to_csv(path, index=False)
    print(f"✅ Created {path}")

def write_xlsx(data):
    df = pd.DataFrame(data)
    path = IDEAL_DIR / "xlsx" / f"{data[0]['planogram_id']}.xlsx"
    df.to_excel(path, index=False, engine='openpyxl')
    print(f"✅ Created {path}")

def write_xls(data):
    if not data:
        return
    path = IDEAL_DIR / "xls" / f"{data[0]['planogram_id']}.xls"
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet('Planogram')
    
    if not data:
        return
        
    headers = list(data[0].keys())
    for col, h in enumerate(headers):
        sheet.write(0, col, h)
        
    for row_idx, row in enumerate(data, start=1):
        for col_idx, h in enumerate(headers):
            sheet.write(row_idx, col_idx, row[h])
            
    workbook.save(str(path))
    print(f"✅ Created {path}")


if __name__ == "__main__":
    print("=" * 60)
    print(" PHASE 7B: GENERATING PROTOTYPE IDEAL PLANOGRAMS")
    print("=" * 60)
    
    create_directories()
    
    # Generate 10 different planograms (P001 to P010)
    for i in range(1, 11):
        pid = f"P{i:03d}"
        data = generate_mock_planogram_data(pid)
        
        # Output all 4 formats for each planogram
        write_json(data)
        write_csv(data)
        write_xlsx(data)
        write_xls(data)
    
    print("\n✅ Phase 7B Dataset Creation Complete!")
