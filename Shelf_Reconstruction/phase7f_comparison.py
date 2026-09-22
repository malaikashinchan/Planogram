"""
Phase 7F: Planogram Comparison Engine
=====================================
Compares the Canonical Ideal Planogram against the reconstructed
Actual Shelf JSON.

Outputs a detailed violation report (Missing, Extra, Misplaced, Facing)
and computes raw compliance metrics for downstream scoring.

Usage:
    python Shelf_Reconstruction/phase7f_comparison.py
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
IDEAL_DIR = BASE_DIR / "Dataset" / "ideal_planograms" / "canonical"
ACTUAL_DIR = BASE_DIR / "outputs" / "actual_shelf"
OUTPUT_DIR = BASE_DIR / "outputs" / "compliance_reports"

def compare_planograms(ideal: dict, actual: dict) -> dict:
    ideal_shelves = {s["shelf_id"]: s["products"] for s in ideal.get("shelves", [])}
    actual_shelves = {s["shelf_id"]: s["products"] for s in actual.get("shelves", [])}
    
    report = {
        "audit_id": actual.get("audit_id"),
        "planogram_id": ideal.get("planogram_id"),
        "missing_products": [],
        "extra_products": [],
        "misplaced_products": [],
        "facing_violations": [],
        "metrics": {}
    }
    
    total_expected_positions = 0
    total_correct_positions = 0
    
    total_expected_products = 0 # sum of expected facings
    total_available_products = 0
    
    unique_expected_skus_count = 0
    correct_facings_count = 0
    
    all_shelf_ids = set(ideal_shelves.keys()) | set(actual_shelves.keys())
    
    for shelf_id in all_shelf_ids:
        ideal_prods = ideal_shelves.get(shelf_id, [])
        actual_prods = actual_shelves.get(shelf_id, [])
        
        # Build dictionaries for easy lookup
        # Positional matching
        ideal_pos_map = {p["position"]: p["sku_id"] for p in ideal_prods}
        actual_pos_map = {p["position"]: p["sku_id"] for p in actual_prods}
        
        # Facing matching (count per SKU)
        ideal_facings = {}
        for p in ideal_prods:
            ideal_facings[p["sku_id"]] = ideal_facings.get(p["sku_id"], 0) + 1
            
        actual_facings = {}
        for p in actual_prods:
            actual_facings[p["sku_id"]] = actual_facings.get(p["sku_id"], 0) + 1
            
        # 1. Product Inventory & Facing Violations
        all_skus = set(ideal_facings.keys()) | set(actual_facings.keys())
        
        for sku in all_skus:
            exp_count = ideal_facings.get(sku, 0)
            act_count = actual_facings.get(sku, 0)
            
            if exp_count > 0:
                unique_expected_skus_count += 1
                total_expected_products += exp_count
                total_available_products += min(act_count, exp_count)
            
            diff = act_count - exp_count
            
            if act_count == 0 and exp_count > 0:
                report["missing_products"].append({"shelf_id": shelf_id, "sku_id": sku, "expected_qty": exp_count})
            elif exp_count == 0 and act_count > 0:
                report["extra_products"].append({"shelf_id": shelf_id, "sku_id": sku, "found_qty": act_count})
            elif exp_count > 0 and act_count > 0 and diff != 0:
                report["facing_violations"].append({
                    "shelf_id": shelf_id,
                    "sku_id": sku,
                    "expected_facings": exp_count,
                    "actual_facings": act_count,
                    "difference": diff
                })
                
            if exp_count > 0 and diff == 0:
                correct_facings_count += 1
                
        # 2. Spatial Arrangement (Misplaced) & Position Accuracy
        for pos, exp_sku in ideal_pos_map.items():
            total_expected_positions += 1
            act_sku = actual_pos_map.get(pos)
            
            if act_sku == exp_sku:
                total_correct_positions += 1
            elif act_sku is not None:
                report["misplaced_products"].append({
                    "shelf_id": shelf_id,
                    "position": pos,
                    "expected_sku_id": exp_sku,
                    "actual_sku_id": act_sku
                })

    # Calculate Raw Metrics
    pos_acc = total_correct_positions / total_expected_positions if total_expected_positions > 0 else 0.0
    avail_rate = total_available_products / total_expected_products if total_expected_products > 0 else 0.0
    facing_comp = correct_facings_count / unique_expected_skus_count if unique_expected_skus_count > 0 else 0.0
    
    report["metrics"] = {
        "position_accuracy": round(pos_acc, 4),
        "availability_rate": round(avail_rate, 4),
        "facing_compliance": round(facing_comp, 4),
    }
    
    return report

if __name__ == "__main__":
    print("=" * 60)
    print(" PHASE 7F: PLANOGRAM COMPARISON ENGINE")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Test against the prototype P001 canonical planogram
    ideal_path = IDEAL_DIR / "P001_canonical.json"
    if not ideal_path.exists():
        print("❌ Cannot run comparison, canonical planogram missing!")
        exit(1)
        
    with open(ideal_path) as f:
        ideal_data = json.load(f)
        
    # 2. Test Controlled Scenarios
    scenarios = {
        "Perfect": {
            "audit_id": "TEST_PERFECT",
            "shelves": [
                {"shelf_id": 1, "products": [
                    {"position": 1, "sku_id": "SKU_001"},
                    {"position": 2, "sku_id": "SKU_001"},
                    {"position": 3, "sku_id": "SKU_002"},
                    {"position": 4, "sku_id": "SKU_004"}
                ]},
                {"shelf_id": 2, "products": [
                    {"position": 1, "sku_id": "SKU_003"},
                    {"position": 2, "sku_id": "SKU_003"},
                    {"position": 3, "sku_id": "SKU_007"},
                    {"position": 4, "sku_id": "SKU_008"}
                ]}
            ]
        },
        "Missing": {
            "audit_id": "TEST_MISSING",
            "shelves": [
                {"shelf_id": 1, "products": [
                    {"position": 1, "sku_id": "SKU_001"},
                    {"position": 2, "sku_id": "SKU_001"},
                    {"position": 3, "sku_id": "SKU_004"}  # Missing SKU_002
                ]}
            ]
        }
    }
    
    for name, actual_data in scenarios.items():
        print(f"\n--- Testing Scenario: {name} ---")
        report = compare_planograms(ideal_data, actual_data)
        out_path = OUTPUT_DIR / f"{report['audit_id']}_report.json"
        
        with open(out_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"Metrics:")
        print(f"  Position Accuracy: {report['metrics']['position_accuracy']:.1%}")
        print(f"  Availability Rate: {report['metrics']['availability_rate']:.1%}")
        print(f"  Facing Compliance: {report['metrics']['facing_compliance']:.1%}")
        
        if report["missing_products"]: print(f"  Missing: {len(report['missing_products'])}")
        if report["extra_products"]: print(f"  Extra: {len(report['extra_products'])}")
        if report["misplaced_products"]: print(f"  Misplaced: {len(report['misplaced_products'])}")
        if report["facing_violations"]: print(f"  Facing Violations: {len(report['facing_violations'])}")
        
    print(f"\n✅ Output compliance reports to {OUTPUT_DIR}")
