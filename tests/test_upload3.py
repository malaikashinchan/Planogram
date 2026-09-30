import requests
from backend.app.core.database import SessionLocal
from backend.app.models import User
from backend.app.auth.service import create_access_token

db = SessionLocal()
user = db.query(User).filter(User.email == 'varshneymalaika@gmail.com').first()

# create a token
token = create_access_token(db, user)

resp = requests.post(
    "http://localhost:8000/api/v1/planograms/upload",
    cookies={"session_token": token},
    files={"file": ("test.csv", b"sku,shelf,position\nSKU001,1,1")},
    data={"name": "Test Planogram", "store_id": ""}
)
print("Response:", resp.status_code)
try:
    print(resp.json())
except:
    print(resp.text)
