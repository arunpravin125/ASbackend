import requests
import json
import datetime

API_URL = "http://localhost:8001"

def test_geocode():
    print("Testing /geocode...")
    try:
        response = requests.post(f"{API_URL}/geocode", json={"location": "Mumbai"})
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_analyze():
    print("\nTesting /analyze...")
    payload = {
        "team_a": "Team A",
        "team_b": "Team B",
        "lat": 18.975,
        "lon": 72.8258,
        "datetime_utc": "2026-02-21T10:00:00",
        "duration_hours": 1.0,
        "timezone": "Asia/Kolkata",
        "ayanamsa": "KRISHNAMURTI"
    }
    try:
        response = requests.post(f"{API_URL}/analyze", json=payload)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Successfully received analysis results.")
            result = response.json()
            print(f"Keys in result: {list(result.keys())}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_archive():
    print("\nTesting /archive...")
    try:
        response = requests.get(f"{API_URL}/archive")
        print(f"Status: {response.status_code}")
        print(f"Archive files: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    s1 = test_geocode()
    s2 = test_analyze()
    s3 = test_archive()
    
    if s1 and s2 and s3:
        print("\nAll API tests PASSED!")
    else:
        print("\nSome API tests FAILED!")
