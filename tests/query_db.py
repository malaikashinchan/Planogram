from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models import Planogram, Store

with SessionLocal() as db:
    for p in db.query(Planogram).all():
        store = db.query(Store).filter(Store.id == p.store_id).first()
        print(f"{p.name} - Store: {store.name if store else 'None'}")
