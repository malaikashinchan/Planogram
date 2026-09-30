import requests
resp = requests.post("http://localhost:8000/api/v1/auth/login", data={"username": "varshneymalaika@gmail.com", "password": "Password123"})
print(resp.text)
