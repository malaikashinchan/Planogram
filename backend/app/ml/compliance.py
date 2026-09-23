def calculate_compliance(reconstruction: list[dict], expected_planogram: list[dict]) -> dict:
    """
    Compares the reconstructed shelf (list of shelves) against the expected planogram version (list of positions).
    
    reconstruction format:
    [
        {"shelf_id": 1, "products": [{"position": 1, "sku_id": "SKU_001"}, ...]},
        ...
    ]
    
    expected_planogram format (from PlanogramPosition DB models):
    [
        {"shelf_id": 1, "position": 1, "product_id": <UUID>}  # Or sku_id depending on how it's fetched
    ]
    """
    # Transform expected_planogram into a dict structured like ideal_shelves: {shelf_id: [{"position": pos, "sku_id": sku}]}
    ideal_shelves = {}
    for pos in expected_planogram:
        sid = pos["shelf_id"]
        if sid not in ideal_shelves:
            ideal_shelves[sid] = []
        ideal_shelves[sid].append({"position": pos["position"], "sku_id": pos["sku_id"]})
        
    actual_shelves = {s["shelf_id"]: s["products"] for s in reconstruction}
    
    report = {
        "missing_products": [],
        "extra_products": [],
        "misplaced_products": [],
        "facing_violations": [],
        "position_accuracy": 0.0,
        "availability_rate": 0.0,
        "facing_compliance": 0.0,
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
        
        ideal_pos_map = {p["position"]: p["sku_id"] for p in ideal_prods}
        actual_pos_map = {p["position"]: p["sku_id"] for p in actual_prods}
        
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
    
    report["position_accuracy"] = round(pos_acc, 4)
    report["availability_rate"] = round(avail_rate, 4)
    report["facing_compliance"] = round(facing_comp, 4)
    
    return report
