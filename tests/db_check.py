from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.planogram import Planogram, PlanogramVersion

db = SessionLocal()
planograms = db.query(Planogram).all()
if planograms:
    print(f"Planograms found: {len(planograms)}")
    for p in planograms:
        print(p.id, p.name)
        versions = db.query(PlanogramVersion).filter(PlanogramVersion.planogram_id == p.id).all()
        print(f"  Versions: {len(versions)}")
        for v in versions:
            print(f"    {v.id}")
        print("---")
else:
    print("No planograms")
