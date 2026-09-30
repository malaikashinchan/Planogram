import requests

resp = requests.post("http://localhost:8000/api/v1/auth/login", data={"username": "varshneymalaika@gmail.com", "password": "Password123"})
token = resp.json().get("access_token")

headers = {"Authorization": f"Bearer {token}"}
resp = requests.get("http://localhost:8000/api/v1/planograms/", headers=headers)
planograms = resp.json()

if planograms:
    pid = planograms[0]["id"]
    print(f"Testing versions for planogram {pid}")
    resp = requests.get(f"http://localhost:8000/api/v1/planograms/{pid}/versions", headers=headers)
    print("Versions:", resp.status_code, resp.text)
