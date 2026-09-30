import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from backend.app.core.database import SessionLocal
from backend.app.models import ActualShelfPosition, Product

db = SessionLocal()
audit_id = "da7cae60-03b9-4cca-8a9a-8c3d355b78f7"

positions = db.query(ActualShelfPosition, Product).join(
    Product, ActualShelfPosition.product_id == Product.id
).filter(
    ActualShelfPosition.audit_id == audit_id
).all()

print("Reconstructed Shelf:")
for pos, prod in sorted(positions, key=lambda x: (x[0].shelf_id, x[0].position)):
    print(f"Shelf {pos.shelf_id}, Pos {pos.position}: {prod.sku_code}")
