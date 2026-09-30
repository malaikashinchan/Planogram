import uuid
from backend.app.core.database import SessionLocal
from backend.app.models import ShelfAudit, PlanogramPosition, Product

audit_id = uuid.UUID("0c7fe404-233a-4b2e-bc40-f54cb40014c9")
db = SessionLocal()
audit = db.query(ShelfAudit).filter(ShelfAudit.id == audit_id).first()

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
print("Expected Planogram:")
print(expected_planogram)
