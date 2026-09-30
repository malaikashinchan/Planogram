from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.planogram import Planogram, PlanogramVersion, PlanogramPosition

db = SessionLocal()
pid = "f48ebe73-f0c7-4a90-9790-7713f51f347f"
version = db.query(PlanogramVersion).filter(PlanogramVersion.planogram_id == pid).first()
if version:
    positions = db.query(PlanogramPosition).filter(PlanogramPosition.planogram_version_id == version.id).all()
    print(f"Positions: {len(positions)}")
    for p in positions:
        print(f"  Shelf: {p.shelf_id}, Pos: {p.position}, Product: {p.product_id}")
