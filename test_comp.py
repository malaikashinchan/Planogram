import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from backend.app.ml.compliance import calculate_compliance

reconstruction = []
expected_planogram = [
    {"shelf_id": 1, "position": 1, "sku_id": "SKU_001"},
    {"shelf_id": 1, "position": 2, "sku_id": "SKU_001"},
    {"shelf_id": 1, "position": 3, "sku_id": "SKU_002"},
]

res = calculate_compliance(reconstruction, expected_planogram)
print(res)
