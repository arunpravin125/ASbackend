import requests
import json

payload = {"username": "testuser_direct", "password": "testpassword123", "email": "test@example.com"}
try:
    res = requests.post("http://127.0.0.1:8001/register", json=payload, timeout=5)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")
except Exception as e:
    print(f"Error: {e}")
