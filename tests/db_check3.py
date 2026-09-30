from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.planogram import Planogram, PlanogramVersion, PlanogramPosition
from backend.app.api.v1.planograms import _version_response
import traceback

db = SessionLocal()
pid = "f48ebe73-f0c7-4a90-9790-7713f51f347f"
version = db.query(PlanogramVersion).filter(PlanogramVersion.planogram_id == pid).first()
if version:
    positions = db.query(PlanogramPosition).filter(PlanogramPosition.planogram_version_id == version.id).all()
    try:
        res = _version_response(version, positions, db)
        print("Success!")
        print(res.model_dump())
    except Exception as e:
        print("FAILED")
        traceback.print_exc()
