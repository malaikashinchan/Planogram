from ultralytics import YOLO
import cv2
from backend.app.services.storage_service import storage
from backend.app.core.database import SessionLocal
from backend.app.models import AuditImage
import numpy as np

db = SessionLocal()
img1 = db.query(AuditImage).filter_by(audit_id='bc44128c-0863-4785-adea-3840b6f929e0').first()
file_bytes = storage.download(img1.storage_key)
np_arr = np.frombuffer(file_bytes, np.uint8)
img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

model = YOLO('runs/grocery_baseline/weights/best.pt')

for conf in [0.1, 0.05, 0.01]:
    results = model(img, conf=conf)
    print(f"Boxes at conf {conf}:", len(results[0].boxes))
