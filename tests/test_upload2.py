import requests
from backend.app.core.database import SessionLocal
from backend.app.models import AuthSession, User
db = SessionLocal()
session = db.query(AuthSession).join(User).filter(User.email == 'varshneymalaika@gmail.com').first()
# Actually, let's just make a mock session in DB or fetch the existing one if any
if session:
    print("Found session for", session.user.email)
    print("Token hash (not raw token):", session.token_hash)
else:
    print("No session found.")
