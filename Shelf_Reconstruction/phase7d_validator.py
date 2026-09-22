"""
Phase 7D: Canonical Planogram Validator
=======================================
Validates the Canonical Planogram against business rules and the Product Master.
If any validation fails, the pipeline immediately halts to prevent
invalid expected data from corrupting the compliance comparison engine.

Checks implemented:
1. Structural: Duplicate/Missing/Non-contiguous positions, Empty shelves.
2. Product: Unknown SKU (must exist in product_master.csv), Invalid format.
3. Planogram: Shelf capacity limit exceeded.

Usage:
    python Shelf_Reconstruction/phase7d_validator.py
"""

import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
MASTER_CSV = BASE_DIR / "Dataset" / "product_master.csv"
MAX_SHELF_CAPACITY = 20 # Prototype validation constraint, not universal retail rule

class PlanogramValidationError(Exception):
    pass

class CanonicalValidator:
    def __init__(self, master_csv_path: Path):
        if not master_csv_path.exists():
            raise FileNotFoundError(f"Product Master not found at {master_csv_path}")
        
        df = pd.read_csv(master_csv_path)
        self.valid_skus = set(df['sku_id'].astype(str).tolist())
        
    def validate(self, canonical_data: dict):
        if not canonical_data:
            raise PlanogramValidationError("Planogram is empty.")
            
        pid = canonical_data.get("planogram_id")
        if not pid:
            raise PlanogramValidationError("Missing planogram_id.")
            
        shelves = canonical_data.get("shelves", [])
        if not shelves:
            raise PlanogramValidationError(f"Planogram {pid} has no shelves.")
            
        shelf_ids_seen = set()
        
        for shelf in shelves:
            sid = shelf.get("shelf_id")
            if sid is None or type(sid) is not int or sid < 1:
                raise PlanogramValidationError(f"Invalid shelf_id: {sid}")
                
            if sid in shelf_ids_seen:
                raise PlanogramValidationError(f"Duplicate shelf_id {sid} in planogram {pid}")
            shelf_ids_seen.add(sid)
            
            products = shelf.get("products", [])
            if not products:
                raise PlanogramValidationError(f"Shelf {sid} is empty.")
                
            if len(products) > MAX_SHELF_CAPACITY:
                raise PlanogramValidationError(f"Shelf {sid} exceeds capacity ({len(products)} > {MAX_SHELF_CAPACITY}).")
                
            positions_seen = set()
            
            for prod in products:
                pos = prod.get("position")
                sku = prod.get("sku_id")
                
                if pos is None or type(pos) is not int or pos < 1:
                    raise PlanogramValidationError(f"Shelf {sid}: Invalid position {pos}")
                    
                if pos in positions_seen:
                    raise PlanogramValidationError(f"Shelf {sid}: Duplicate position {pos}")
                positions_seen.add(pos)
                
                if not sku:
                    raise PlanogramValidationError(f"Shelf {sid}, Pos {pos}: Missing SKU")
                    
                if str(sku) not in self.valid_skus:
                    raise PlanogramValidationError(f"Shelf {sid}, Pos {pos}: Unknown SKU '{sku}' not in Product Master")
                    
            # Check for missing/non-contiguous positions
            expected_positions = set(range(1, max(positions_seen) + 1))
            missing = expected_positions - positions_seen
            if missing:
                raise PlanogramValidationError(f"Shelf {sid}: Missing contiguous positions {sorted(missing)}")
                
        return True


if __name__ == "__main__":
    print("=" * 60)
    print(" PHASE 7D: RUNNING CANONICAL VALIDATOR TESTS")
    print("=" * 60)
    
    validator = CanonicalValidator(MASTER_CSV)
    
    # Test 1: Valid Planogram
    valid_p = {
        "planogram_id": "P_TEST",
        "shelves": [
            {"shelf_id": 1, "products": [
                {"position": 1, "sku_id": "SKU_001"},
                {"position": 2, "sku_id": "SKU_002"}
            ]}
        ]
    }
    print("Testing Valid Planogram...")
    validator.validate(valid_p)
    print("✅ Passed!")
    
    # Scenarios for errors
    scenarios = {
        "Duplicate Position": {
            "planogram_id": "P_TEST", "shelves": [
                {"shelf_id": 1, "products": [{"position": 1, "sku_id": "SKU_001"}, {"position": 1, "sku_id": "SKU_002"}]}
            ]
        },
        "Missing Position": {
            "planogram_id": "P_TEST", "shelves": [
                {"shelf_id": 1, "products": [{"position": 1, "sku_id": "SKU_001"}, {"position": 3, "sku_id": "SKU_002"}]}
            ]
        },
        "Unknown SKU": {
            "planogram_id": "P_TEST", "shelves": [
                {"shelf_id": 1, "products": [{"position": 1, "sku_id": "SKU_999"}]}
            ]
        },
        "Shelf Overflow": {
            "planogram_id": "P_TEST", "shelves": [
                {"shelf_id": 1, "products": [{"position": i, "sku_id": "SKU_001"} for i in range(1, 22)]}
            ]
        }
    }
    
    for name, data in scenarios.items():
        print(f"\nTesting {name}...")
        try:
            validator.validate(data)
            print(f"❌ FAIL: Expected validation error for {name}")
        except PlanogramValidationError as e:
            print(f"✅ Caught expected error: {e}")
