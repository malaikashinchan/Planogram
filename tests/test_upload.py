import requests
from backend.app.core.database import SessionLocal
from backend.app.models import AuthSession, User
db = SessionLocal()
session = db.query(AuthSession).join(User).filter(User.email == 'varshneymalaika@gmail.com').first()
token = session.session_token

resp = requests.post(
    "http://localhost:8000/api/v1/planograms/upload",
    cookies={"session_token": token},
    files={"file": ("test.csv", b"dummy")},
    data={"name": "Test Planogram", "store_id": ""}
)
print("Response:", resp.status_code)
try:
    print(resp.json())
except:
    print(resp.text)
