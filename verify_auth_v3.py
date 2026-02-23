import requests
import time
import sys

def log(msg):
    print(msg)
    sys.stdout.flush()

BASE_URL = "http://127.0.0.1:8000"

def test_auth_flow():
    username = f"testuser_{int(time.time())}"
    password = "testpassword123"
    
    log(f"--- Testing registration for {username} ---")
    try:
        reg_payload = {"username": username, "password": password, "email": "test@example.com"}
        res = requests.post(f"{BASE_URL}/register", json=reg_payload, timeout=10)
    except Exception as e:
        log(f"Register Request Failed: {e}")
        return
    
    if res.status_code == 500:
        try:
            det = res.json().get("detail", {})
            log(f"Register 500 Error: {det.get('error')}")
            log(f"Register Traceback: {det.get('traceback')}")
        except:
            log(f"Register 500 (Not JSON): {res.text}")
        return
    
    if res.status_code != 200:
        log(f"Register Failed with {res.status_code}: {res.text}")
        return
    
    log("\n--- Testing login ---")
    try:
        login_data = {"username": username, "password": password}
        res = requests.post(f"{BASE_URL}/login", data=login_data, timeout=10)
        log(f"Login Status: {res.status_code}")
        login_res = res.json()
        log(f"Login Response: {login_res}")
    except Exception as e:
        log(f"Login Failed: {e}")
        return
    
    if res.status_code == 200:
        token = login_res["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        log("\n--- Testing analysis (expect 403) ---")
        analyze_payload = {
            "team_a": "Team A", "team_b": "Team B", 
            "lat": 19.076, "lon": 72.877, 
            "datetime_utc": "2026-02-17T19:00:00", 
            "duration_hours": 3.5, "timezone": "Asia/Kolkata"
        }
        try:
            res = requests.post(f"{BASE_URL}/analyze", json=analyze_payload, headers=headers, timeout=60)
            log(f"Analyze Status (Pre-approval): {res.status_code}")
            
            log("\n--- Approving user in DB ---")
            import motor.motor_asyncio
            import asyncio
            async def approve():
                client = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://arunpravin125_db_user:oDKR4QFbNjWOUT38@cluster0.iclvilw.mongodb.net/?appName=Cluster0")
                db = client['kp_astrologer_db']
                await db['user_licenses'].update_one({"username": username}, {"$set": {"status": True}})
            asyncio.run(approve())
            log("User approved.")

            log("\n--- Testing analysis (expect 200) ---")
            res = requests.post(f"{BASE_URL}/analyze", json=analyze_payload, headers=headers, timeout=60)
            log(f"Analyze Status (Post-approval): {res.status_code}")
            if res.status_code == 200:
                log("\n[SUCCESS] Full Flow Verified Successfully!")
            else:
                log(f"\n[FAILURE] Final Analysis failed: {res.text}")
        except Exception as e:
            log(f"Analyze Failed: {e}")
            
    log("\n--- Testing Forgot Password ---")
    try:
        res = requests.post(f"{BASE_URL}/forgot-password", json={"username": username}, timeout=10)
        log(f"Forgot Status: {res.status_code}")
        log(f"Forgot Response: {res.json()}")
    except Exception as e:
        log(f"Forgot Failed: {e}")
    
    log("\n--- Testing Reset Password ---")
    try:
        reset_payload = {
            "username": username,
            "otp": "123456",
            "new_password": "newpassword123"
        }
        res = requests.post(f"{BASE_URL}/reset-password", json=reset_payload, timeout=10)
        log(f"Reset Status: {res.status_code}")
        log(f"Reset Response: {res.json()}")
    except Exception as e:
        log(f"Reset Failed: {e}")

if __name__ == "__main__":
    test_auth_flow()
