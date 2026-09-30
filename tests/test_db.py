import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from backend.app.core.database import SessionLocal
from backend.app.models import PlanogramPosition, Product

db = SessionLocal()
pv_id = "858c343b-9eb5-4505-845e-a11e0ededaf7"
expected_positions_db = db.query(PlanogramPosition, Product).join(
    Product, PlanogramPosition.product_id == Product.id
).filter(
    PlanogramPosition.planogram_version_id == pv_id
).all()

print(f"Found {len(expected_positions_db)} expected positions.")
