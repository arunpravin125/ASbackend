import requests
import json

def test_registration():
    url = "http://127.0.0.1:8000/register"
    payload = {
        "username": "testuser_api_debug",
        "password": "password123",
        "email": "debug@example.com"
    }
    headers = {"Content-Type": "application/json"}
    
    print(f"Making request to {url}...")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print("Response Headers:", response.headers)
        try:
            res_json = response.json()
            print("Response JSON:", json.dumps(res_json, indent=2))
            if "detail" in res_json and isinstance(res_json["detail"], dict) and "traceback" in res_json["detail"]:
                print("\nSERVER TRACEBACK:")
                print(res_json["detail"]["traceback"])
        except:
            print("Response Text (Not JSON):", response.text)
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_registration()
