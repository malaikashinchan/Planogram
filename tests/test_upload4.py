import requests
from backend.app.core.database import SessionLocal
from backend.app.models import User
from backend.app.auth.service import _generate_token, _hash_token
from backend.app.models.auth import AuthSession
from datetime import datetime, timedelta, timezone

db = SessionLocal()
user = db.query(User).filter(User.email == 'varshneymalaika@gmail.com').first()

token = _generate_token()
db.add(AuthSession(
    user_id=user.id,
    token_hash=_hash_token(token),
    expires_at=datetime.now(timezone.utc) + timedelta(days=30)
))
db.commit()

resp = requests.post(
    "http://localhost:8000/api/v1/planograms/upload",
    cookies={"session_token": token},
    files={"file": ("test.csv", b"sku_id,shelf_id,position\nSKU001,1,1")},
    data={"name": "Test Planogram", "store_id": ""}
)
print("Response:", resp.status_code)
try:
    print(resp.json())
except:
    print(resp.text)
