import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from apscheduler.schedulers.background import BackgroundScheduler
from database import get_db_connection, init_db
from pipeline import run_data_pipeline
from ml_model import predict_district_risks, run_dbscan_clustering

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Stubble Burning Early-Warning & Farmer Advisory System API")

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request bodies
class FarmerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=10, max_length=15)
    district_id: int
    language: str = Field(default="Hindi", description="Hindi or English")

# Initialize SQLite database
init_db()

# Optional Twilio config (Mocked by default)
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

def send_sms(phone: str, message: str) -> str:
    """Sends SMS using Twilio if configured, otherwise returns simulated status."""
    if TWILIO_SID and TWILIO_AUTH_TOKEN and TWILIO_NUMBER:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message,
                from_=TWILIO_NUMBER,
                to=phone
            )
            return "Sent"
        except Exception as e:
            print(f"Twilio sending failed: {e}")
            return "Failed (Twilio Error)"
    return "Simulated"

def generate_advisory_message(district_name: str, language: str) -> str:
    """Generates the bilingual advisory containing warnings, rental contact, and buyback info."""
    if language.lower() == "hindi":
        return (
            f"[चेतावनी] {district_name} में अगले 24-48 घंटों में वायु गुणवत्ता सूचकांक (AQI) खतरनाक "
            f"स्तर पर पहुँचने की आशंका है। कृपया पराली न जलाएं। "
            f"मशीन किराये पर लेने हेतु अपने नजदीकी हैप्पी सीडर केंद्र (कॉल: 1800-123-4567) से संपर्क करें "
            f"या पराली बेचने के लिए सरकारी बायोमास केंद्र (कॉल: 1800-987-6543) पर संपर्क करें।"
        )
    else:
        return (
            f"[ALERT] Air Quality Index (AQI) is predicted to reach dangerous levels in {district_name} "
            f"over the next 24-48 hours due to stubble burning risk. DO NOT BURN residue. "
            f"Rent Happy Seeder/Super SMS machinery from your nearest cooperative (call: 1800-123-4567) "
            f"or sell crop residue to biomass buyback centers (call: 1800-987-6543)."
        )

def process_and_send_advisories():
    """Finds farmers in high-risk districts and logs/sends advisory SMS messages."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch districts with 'High' or 'Medium' risk predictions
    cursor.execute("""
    SELECT p.district_id, d.name as district_name, p.risk_level
    FROM predictions p
    JOIN districts d ON p.district_id = d.id
    WHERE p.id IN (SELECT MAX(id) FROM predictions GROUP BY district_id)
      AND p.risk_level IN ('High', 'Medium')
    """)
    flagged_districts = {row['district_id']: dict(row) for row in cursor.fetchall()}
    
    if not flagged_districts:
        conn.close()
        return {"status": "No high/medium risk districts to advise."}
        
    # 2. Find farmers registered in these districts
    cursor.execute("""
    SELECT f.id, f.name, f.phone, f.district_id, f.language
    FROM farmers f
    WHERE f.district_id IN ({})
    """.format(",".join(map(str, flagged_districts.keys()))))
    farmers = [dict(row) for row in cursor.fetchall()]
    
    advisories_generated = 0
    timestamp = datetime.now().isoformat()
    
    for farmer in farmers:
        dist_info = flagged_districts[farmer['district_id']]
        msg = generate_advisory_message(dist_info['district_name'], farmer['language'])
        
        # Check if we already sent an advisory to this farmer today to avoid spam
        cursor.execute("""
        SELECT COUNT(*) FROM advisories 
        WHERE farmer_id = ? AND date(timestamp) = date('now')
        """, (farmer['id'],))
        if cursor.fetchone()[0] > 0:
            continue
            
        status = send_sms(farmer['phone'], msg)
        
        cursor.execute("""
        INSERT INTO advisories (farmer_id, district_id, timestamp, message, status)
        VALUES (?, ?, ?, ?, ?)
        """, (farmer['id'], farmer['district_id'], timestamp, msg, status))
        advisories_generated += 1
        
    conn.commit()
    conn.close()
    return {"status": "Success", "advisories_sent": advisories_generated}

# API Endpoints
@app.get("/api/districts")
def get_districts():
    """Returns the list of all districts with current weather, AQI, fires, and predictions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # SQL JOIN query to assemble full district status
        cursor.execute("""
        SELECT d.id, d.name, d.state, d.latitude, d.longitude,
               w.aqi, w.pm25, w.pm10, w.wind_speed, w.wind_dir, w.humidity, w.timestamp as weather_timestamp,
               p.risk_level, p.confidence as prediction_confidence, p.prediction_date, p.features as prediction_features,
               (SELECT COUNT(*) FROM hotspots h WHERE h.district_id = d.id) as active_fires
        FROM districts d
        LEFT JOIN (
            SELECT district_id, aqi, pm25, pm10, wind_speed, wind_dir, humidity, timestamp
            FROM weather_aqi
            WHERE id IN (SELECT MAX(id) FROM weather_aqi GROUP BY district_id)
        ) w ON d.id = w.district_id
        LEFT JOIN (
            SELECT district_id, risk_level, confidence, prediction_date, features
            FROM predictions
            WHERE id IN (SELECT MAX(id) FROM predictions GROUP BY district_id)
        ) p ON d.id = p.district_id
        """)
        rows = cursor.fetchall()
        districts = []
        for r in rows:
            d = dict(r)
            if d['prediction_features']:
                d['prediction_features'] = json.loads(d['prediction_features'])
            districts.append(d)
        return districts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/hotspots")
def get_hotspots():
    """Returns active hotspots and DBSCAN spatial clusters."""
    try:
        cluster_res = run_dbscan_clustering()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT h.latitude, h.longitude, h.confidence, h.acq_date, h.acq_time, d.name as district_name
        FROM hotspots h
        LEFT JOIN districts d ON h.district_id = d.id
        """)
        hotspots = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {
            "hotspots": hotspots,
            "clusters": cluster_res["clusters"],
            "noise": cluster_res["noise"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh")
def refresh_data(simulate: bool = True):
    """Refreshes NASA FIRMS/Open-Meteo data, runs ML predictions, and generates advisories."""
    try:
        run_data_pipeline(simulate=simulate)
        predict_district_risks()
        adv_res = process_and_send_advisories()
        return {
            "status": "success",
            "message": "Data refreshed, predictions updated, and advisories dispatched.",
            "advisory_status": adv_res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predictions")
def get_predictions():
    """Returns predicted high-risk zones/districts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT p.id, p.prediction_date, p.risk_level, p.confidence, p.features, d.name as district_name, d.state
        FROM predictions p
        JOIN districts d ON p.district_id = d.id
        WHERE p.id IN (SELECT MAX(id) FROM predictions GROUP BY district_id)
        """)
        rows = cursor.fetchall()
        predictions = []
        for r in rows:
            p = dict(r)
            if p['features']:
                p['features'] = json.loads(p['features'])
            predictions.append(p)
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/farmers")
def create_farmer(farmer: FarmerCreate):
    """Registers a farmer in the system."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO farmers (name, phone, district_id, language)
        VALUES (?, ?, ?, ?)
        """, (farmer.name, farmer.phone, farmer.district_id, farmer.language))
        conn.commit()
        return {"status": "success", "message": "Farmer registered successfully."}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Phone number already registered.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/farmers")
def get_farmers():
    """Returns registered farmers."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT f.id, f.name, f.phone, f.language, d.name as district_name, d.state
    FROM farmers f
    JOIN districts d ON f.district_id = d.id
    """)
    farmers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return farmers

@app.get("/api/advisories")
def get_advisories():
    """Returns advisory logs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT a.id, a.timestamp, a.message, a.status, f.name as farmer_name, f.phone as farmer_phone, d.name as district_name
    FROM advisories a
    JOIN farmers f ON a.farmer_id = f.id
    JOIN districts d ON a.district_id = d.id
    ORDER BY a.id DESC
    """)
    advisories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return advisories

@app.post("/api/trigger-advisory")
def trigger_advisory_manual():
    """Triggers advisory processing manually."""
    try:
        res = process_and_send_advisories()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# APScheduler Setup for cron-style refreshes every 4 hours
scheduler = BackgroundScheduler()
scheduler.add_job(func=refresh_data, trigger="interval", hours=4, args=[False]) # live refresh
scheduler.start()

# Shutdown scheduler on application exit
@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

if __name__ == "__main__":
    import uvicorn
    # Pre-calculate predictions on start
    try:
        predict_district_risks()
        print("Initial predictions calculated.")
    except Exception as e:
        print(f"Warning: could not calculate initial predictions: {e}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
