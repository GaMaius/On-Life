import requests
import time

print("Testing AI Endpoint...")
try:
    res = requests.post('http://localhost:5000/api/ai', json={"message": "안녕! 너는 누구니?"}, timeout=30)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.json()}")
except Exception as e:
    print(f"Error: {e}")
