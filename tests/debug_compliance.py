import uuid
from backend.app.core.database import SessionLocal
from backend.app.models import ShelfAudit, PlanogramPosition, Product
from backend.app.ml.compliance import calculate_compliance
from backend.app.ml.reconstruction import reconstruct_shelf
from backend.app.ml.detection import run_yolo_detection
from backend.app.ml.recognition import run_recognition

audit_id = uuid.UUID("0c7fe404-233a-4b2e-bc40-f54cb40014c9")
db = SessionLocal()
audit = db.query(ShelfAudit).filter(ShelfAudit.id == audit_id).first()

# Mock detections
detections_dict = run_yolo_detection("dummy.jpg")
recognitions_dict = run_recognition("dummy.jpg", detections_dict, audit.organization_id)
reconstruction = reconstruct_shelf(detections_dict, recognitions_dict)

expected_positions_db = db.query(PlanogramPosition, Product).join(
    Product, PlanogramPosition.product_id == Product.id
).filter(
    PlanogramPosition.planogram_version_id == audit.planogram_version_id
).all()

expected_planogram = [
    {
        "shelf_id": pos.shelf_id,
        "position": pos.position,
        "sku_id": prod.sku_code
    }
    for pos, prod in expected_positions_db
]

compliance_data = calculate_compliance(reconstruction, expected_planogram)
print(compliance_data["missing_products"])
print(compliance_data["extra_products"])
