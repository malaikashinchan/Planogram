import uuid
from backend.app.core.database import SessionLocal
from backend.app.models import ShelfAudit, PlanogramPosition, Product
from backend.app.ml.compliance import calculate_compliance

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

# Use a mock reconstruction that matches what the user's screenshot has
# In the user's screenshot:
# Misplaced Marlboro (Shelf 1, Pos 1) -> Actually, we don't know the exact reconstruction.
# Let's just create a dummy reconstruction with an empty shelf to trigger MISSING_PRODUCTs
reconstruction = [
    {"shelf_id": 1, "products": []},
    {"shelf_id": 2, "products": []}
]

compliance_data = calculate_compliance(reconstruction, expected_planogram)
print("MISSING PRODUCTS:")
for mp in compliance_data["missing_products"]:
    print(mp)
