from backend.app.core.database import SessionLocal
from backend.app.models.user import User

db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(u.email)
