from fastapi import FastAPI, HTTPException, Body, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import sys
import json
import pandas as pd
import datetime
import swisseph as swe
from fastapi.middleware.cors import CORSMiddleware
import traceback
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Add the current directory to sys.path to allow imports from kp_core
backend_root = os.path.dirname(os.path.abspath(__file__))
if backend_root not in sys.path:
    sys.path.append(backend_root)

from kp_core.kp_engine import KPEngine, PlanetNameUtils
from kp_core.timeline_generator import TimelineGenerator
from kp_core.analysis_engine import AnalysisEngine
import logic_extensions
import auth
from database import init_db
from models.user_license import UserLicense
from models.prediction import Prediction
import uuid

app = FastAPI(title="KP AI Astrologer API")

@app.on_event("startup")
async def startup_event():
    try:
        await init_db()
    except Exception as e:
        print(f"Database initialization failed: {e}")
    
    # Start the periodic ping job to keep the server awake
    start_ping_job()

async def ping_server():
    api_url = os.getenv("API_URL", "https://asbackend-1-5q6u.onrender.com/")
    if not api_url:
        print("API_URL environment variable is not set. Skipping ping.")
        return
        
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(api_url)
            if res.status_code == 200:
                print("GET request sent successfully")
            else:
                print(f"GET request failed with status code: {res.status_code}")
    except Exception as e:
        print(f"Error while sending request: {e}")

def start_ping_job():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(ping_server, 'interval', minutes=14)
    scheduler.start()
    print("Ping job started. Running every 14 minutes.")

# Enable CORS for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set Swiss Ephemeris path
swe.set_ephe_path(os.path.join(backend_root, 'swisseph'))

ARCHIVE_DIR = os.path.join(backend_root, "match_archive")
os.makedirs(ARCHIVE_DIR, exist_ok=True)

class GeocodeRequest(BaseModel):
    location: str

class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class ForgotPasswordRequest(BaseModel):
    username: str

class ResetPasswordRequest(BaseModel):
    username: str
    otp: str
    new_password: str

class AnalysisRequest(BaseModel):
    team_a: str
    team_b: str
    lat: float
    lon: float
    datetime_utc: str  # ISO format
    duration_hours: float
    timezone: str
    ayanamsa: Optional[str] = "KRISHNAMURTI"
    house_weights: Optional[Dict[int, float]] = None
    timeline_weights: Optional[Dict[str, Any]] = None


@app.post("/register")
async def register(request: UserRegister):
    try:
        print(f"DEBUG: Registering user {request.username}")
        existing_user = await UserLicense.find_one(UserLicense.username == request.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        new_user = UserLicense(
            userId=str(uuid.uuid4()),
            username=request.username,
            email=request.email,
            hashed_password=auth.get_password_hash(request.password),
            status=False # Default to false for owner approval
        )
        await new_user.insert()
        return {"message": "Registration successful. Please wait for owner approval."}
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Registration error: {e}")
        print(error_details)
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": error_details})

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await UserLicense.find_one(UserLicense.username == form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer", "status": user.status}

@app.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    user = await UserLicense.find_one(UserLicense.username == request.username)
    if not user:
         return {"message": "If the user exists, an OTP has been sent."} # Security: don't reveal user existence
    
    # In a real app, send OTP via email. Here we just set it systemically for demo.
    otp = "123456" # Hardcoded for demo/verification
    user.reset_otp = otp
    await user.save()
    return {"message": "OTP generated. Use /reset-password with OTP 123456."}

@app.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    user = await UserLicense.find_one(UserLicense.username == request.username)
    if not user or user.reset_otp != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    user.hashed_password = auth.get_password_hash(request.new_password)
    user.reset_otp = None
    await user.save()
    return {"message": "Password reset successful"}

@app.post("/geocode")
async def geocode(request: GeocodeRequest):
    from geopy.geocoders import Nominatim
    try:
        geolocator = Nominatim(user_agent="kp_ai_astrologer_backend")
        location = geolocator.geocode(request.location)
        if location:
            return {"lat": location.latitude, "lon": location.longitude}
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="Location not found")

@app.post("/analyze")
async def analyze(request: AnalysisRequest, current_user: UserLicense = Depends(auth.get_approved_user)):
    try:
        dt_utc = datetime.datetime.fromisoformat(request.datetime_utc)
        
        # Initialize Engine
        engine = KPEngine(dt_utc, request.lat, request.lon, ayanamsa=request.ayanamsa)
        
        # Initialize analysis engine with weights
        analysis_engine = AnalysisEngine(
            engine, request.team_a, request.team_b, 
            house_weights=request.house_weights, 
            timeline_weights=request.timeline_weights
        )
        
        # Perform Analysis (matching original run_analysis logic)
        muhurta_analysis = analysis_engine.analyze_muhurta_chart(scoring_method='authentic_kp')
        planets_df = analysis_engine.get_all_planet_details_df()
        cusps_df = engine.get_all_cusps_df()
        
        # 1. Ascendant Timeline
        asc_timeline_gen = TimelineGenerator(engine, 'Ascendant')
        asc_timeline_raw = asc_timeline_gen.generate_aggregated_timeline_df(dt_utc, request.duration_hours)
        asc_timeline_df, asc_timeline_analysis = analysis_engine.analyze_aggregated_timeline(asc_timeline_raw)
        print(f"DEBUG: asc_timeline_df columns: {asc_timeline_df.columns.tolist()}")
        
        # 2. Moon SSSL Timeline (detailed)
        moon_timeline_gen = TimelineGenerator(engine, 'Moon')
        moon_sssl_raw = moon_timeline_gen.generate_detailed_timeline_df(dt_utc, request.duration_hours)
        moon_timeline_df, moon_timeline_analysis = analysis_engine.analyze_timeline(moon_sssl_raw['sssl_timeline'])
        print(f"DEBUG: moon_timeline_df columns: {moon_timeline_df.columns.tolist()}")
        
        # 3. Simple Lagna-Based Reference Timeline
        # Use target_tz from match_details or default to Asia/Kolkata
        target_tz = request.timezone
        
        simplified_timeline = logic_extensions.generate_lagna_based_timeline(
            engine, analysis_engine, dt_utc, request.duration_hours, target_tz,
            request.team_a, request.team_b,
            combined_adjustment_map=request.timeline_weights.get('combined_adjustment_map') if request.timeline_weights else None,
            combined_adjustment_strength=request.timeline_weights.get('combined_adjustment_strength') if request.timeline_weights else 0.0
        )
        
        # 4. Reference Style Consolidated Timeline (Image Style)
        reference_timeline = logic_extensions.build_reference_style_timeline(
            simplified_timeline, dt_utc, request.duration_hours, target_tz
        )
        
        # 5. Assign wicket events for reference timeline
        reference_timeline = logic_extensions.assign_wicket_events_by_rules(
            reference_timeline, dt_utc, request.duration_hours
        )

        # Prepare response
        results = {
            "muhurta_analysis": muhurta_analysis,
            "planets_df": planets_df.to_json(orient='split'),
            "cusps_df": cusps_df.to_json(orient='split'),
            "asc_timeline_df": asc_timeline_df.to_json(orient='split'),
            "asc_timeline_analysis": asc_timeline_analysis,
            "moon_timeline_df": moon_timeline_df.to_json(orient='split'),
            "moon_timeline_analysis": moon_timeline_analysis,
            "detailed_timelines": {
                **{k: v.to_json(orient='split') for k, v in moon_sssl_raw.items() if k != 'sssl_timeline'},
                "sssl_timeline": moon_timeline_df.to_json(orient='split')
            },
            "simplified_timeline_df": simplified_timeline.to_json(orient='split'),
            "ref_timeline_df": reference_timeline.to_json(orient='split'),
            "match_details": {
                "team_a": request.team_a,
                "team_b": request.team_b,
                "lat": request.lat,
                "lon": request.lon,
                "datetime_utc": dt_utc.isoformat(),
                "duration_hours": request.duration_hours,
                "timezone": request.timezone,
                "ayanamsa": request.ayanamsa
            },
            "status": "success"
        }
        
        # Log prediction
        try:
            current_user.predictionCount += 1
            await current_user.save()
            
            prediction = Prediction(
                userId=current_user.userId,
                team_a=request.team_a,
                team_b=request.team_b,
                datetime_utc=dt_utc,
                lat=request.lat,
                lon=request.lon,
                muhurta_analysis=results.get("muhurta_analysis")
            )
            await prediction.insert()
        except Exception as log_err:
            print(f"Failed to log prediction: {log_err}")
            
        return results
    except Exception as e:
        error_details = traceback.format_exc()
        print(error_details)
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": error_details})

@app.get("/archive")
async def list_archive():
    files = [f for f in os.listdir(ARCHIVE_DIR) if f.endswith('.json')]
    return {"files": sorted(files, reverse=True)}

@app.get("/archive/{filename}")
async def get_archive_item(filename: str):
    filepath = os.path.join(ARCHIVE_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data

@app.post("/save")
async def save_analysis_api(data: Dict[str, Any] = Body(...)):
    try:
        match_details = data.get('match_details', {})
        team_a = match_details.get('team_a', 'Unknown').replace(" ", "-")
        team_b = match_details.get('team_b', 'Unknown').replace(" ", "-")
        
        dt_str = match_details.get('datetime_utc')
        if dt_str:
            dt = datetime.datetime.fromisoformat(dt_str)
            date_str = dt.date().strftime('%Y-%m-%d')
        else:
            date_str = datetime.date.today().strftime('%Y-%m-%d')
            
        filename = f"{date_str}_{team_a}_vs_{team_b}.json"
        filepath = os.path.join(ARCHIVE_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        
        return {"status": "success", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
