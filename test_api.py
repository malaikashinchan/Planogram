import requests
import json
token_resp = requests.post("http://localhost:8000/api/v1/auth/login", data={"username": "manager@test.com", "password": "password"})
token = token_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
r = requests.get("http://localhost:8000/api/v1/audits/bc44128c-0863-4785-adea-3840b6f929e0/violations", headers=headers)
print(json.dumps(r.json(), indent=2))
