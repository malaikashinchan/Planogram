from backend.app.core.database import SessionLocal
from backend.app.models import MLTrainingSample, SampleStatus
db = SessionLocal()
samples = db.query(MLTrainingSample).order_by(MLTrainingSample.created_at.desc()).limit(5).all()
for s in samples:
    print(f"ID: {s.id}, Key: {s.crop_storage_key}, Status: {s.status}")
