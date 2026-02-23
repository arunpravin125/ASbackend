
import requests
import json
import traceback

URL = "http://127.0.0.1:8000/analyze"
PAYLOAD = {
    "team_a": "Team A",
    "team_b": "Team B",
    "lat": 19.0760,
    "lon": 72.8777,
    "datetime_utc": "2026-02-21T10:00:00Z",
    "duration_hours": 1.0,
    "timezone": "Asia/Kolkata",
    "ayanamsa": "KRISHNAMURTI"
}

output = []
try:
    output.append(f"Sending request to {URL}...")
    response = requests.post(URL, json=PAYLOAD)
    output.append(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        output.append("Response JSON:")
        output.append(json.dumps(data, indent=2))
    except:
        output.append("Response Text:")
        output.append(response.text)
except Exception as e:
    output.append(f"Connection Error: {e}")
    output.append(traceback.format_exc())

with open("verify_api_res.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))
print("Done writing to verify_api_res.txt")
