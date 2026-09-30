import asyncio
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

app = FastAPI()

def dependency():
    return "authorized!"

def require_roles():
    return Depends(dependency)

@app.post("/test")
def test_route(user: str = require_roles()):
    return {"user": user}

client = TestClient(app)
resp = client.post("/test")
print("Response:", resp.status_code, resp.json())
