import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from backend.app.core.database import SessionLocal
from backend.app.models.store import Store
import uuid

db = SessionLocal()
org_id = uuid.UUID('5ba63bca-2caa-4bb5-a3d8-1a150377b855')
store_id = uuid.UUID('2bbc4d40-78d9-446e-a183-7cc95cfe803f')

store = db.query(Store).filter(Store.id == store_id).first()
if store:
    print(f"Store found! Org ID: {store.organization_id}")
    if store.organization_id == org_id:
        print("Org ID matches!")
    else:
        print("Org ID does NOT match.")
else:
    print("Store not found at all in DB.")
