import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "system.db")

# Ensure the data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# List of key districts with coordinates for demo purposes
DEFAULT_DISTRICTS = [
    # Punjab
    {"name": "Amritsar", "state": "Punjab", "lat": 31.6340, "lon": 74.8723},
    {"name": "Jalandhar", "state": "Punjab", "lat": 31.3260, "lon": 75.5762},
    {"name": "Ludhiana", "state": "Punjab", "lat": 30.9010, "lon": 75.8573},
    {"name": "Patiala", "state": "Punjab", "lat": 30.3398, "lon": 76.3869},
    {"name": "Bathinda", "state": "Punjab", "lat": 30.2110, "lon": 74.9454},
    {"name": "Sangrur", "state": "Punjab", "lat": 30.2292, "lon": 75.8428},
    {"name": "Firozpur", "state": "Punjab", "lat": 30.9256, "lon": 74.6121},
    {"name": "Gurdaspur", "state": "Punjab", "lat": 32.0415, "lon": 75.4053},
    {"name": "Moga", "state": "Punjab", "lat": 30.8170, "lon": 75.1722},
    {"name": "Tarn Taran", "state": "Punjab", "lat": 31.4520, "lon": 74.9220},
    
    # Haryana
    {"name": "Karnal", "state": "Haryana", "lat": 29.6857, "lon": 76.9905},
    {"name": "Hisar", "state": "Haryana", "lat": 29.1492, "lon": 75.7217},
    {"name": "Rohtak", "state": "Haryana", "lat": 28.8955, "lon": 76.6066},
    {"name": "Gurugram", "state": "Haryana", "lat": 28.4595, "lon": 77.0266},
    {"name": "Faridabad", "state": "Haryana", "lat": 28.4089, "lon": 77.3178},
    {"name": "Sonipat", "state": "Haryana", "lat": 28.9931, "lon": 77.0151},
    {"name": "Panipat", "state": "Haryana", "lat": 29.3909, "lon": 76.9635},
    {"name": "Sirsa", "state": "Haryana", "lat": 29.5312, "lon": 75.0336},
    {"name": "Ambala", "state": "Haryana", "lat": 30.3782, "lon": 76.7767},
    {"name": "Kurukshetra", "state": "Haryana", "lat": 29.9695, "lon": 76.8497},

    # NCR
    {"name": "Delhi Central", "state": "Delhi", "lat": 28.6139, "lon": 77.2090},
    {"name": "Noida", "state": "Uttar Pradesh (NCR)", "lat": 28.5355, "lon": 77.3910},
    {"name": "Ghaziabad", "state": "Uttar Pradesh (NCR)", "lat": 28.6692, "lon": 77.4538}
]

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create Districts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS districts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        state TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL
    )
    """)
    
    # Create Hotspots Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hotspots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        confidence REAL,
        acq_date TEXT NOT NULL,
        acq_time TEXT,
        district_id INTEGER,
        FOREIGN KEY (district_id) REFERENCES districts (id)
    )
    """)
    
    # Create Weather/AQI Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weather_aqi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        district_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        aqi INTEGER,
        pm25 REAL,
        pm10 REAL,
        wind_speed REAL,
        wind_dir REAL,
        humidity REAL,
        FOREIGN KEY (district_id) REFERENCES districts (id)
    )
    """)
    
    # Create Predictions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        district_id INTEGER NOT NULL,
        prediction_date TEXT NOT NULL,
        risk_level TEXT NOT NULL, -- 'Low', 'Medium', 'High'
        confidence REAL NOT NULL,
        features TEXT, -- JSON string of features used for the prediction
        FOREIGN KEY (district_id) REFERENCES districts (id)
    )
    """)
    
    # Create Farmers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS farmers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        district_id INTEGER NOT NULL,
        language TEXT NOT NULL, -- 'Hindi' or 'English'
        FOREIGN KEY (district_id) REFERENCES districts (id)
    )
    """)
    
    # Create Advisories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS advisories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER NOT NULL,
        district_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL, -- 'Sent', 'Failed', 'Simulated'
        FOREIGN KEY (farmer_id) REFERENCES farmers (id),
        FOREIGN KEY (district_id) REFERENCES districts (id)
    )
    """)
    
    # Insert default districts
    for d in DEFAULT_DISTRICTS:
        cursor.execute("""
        INSERT OR IGNORE INTO districts (name, state, latitude, longitude)
        VALUES (?, ?, ?, ?)
        """, (d["name"], d["state"], d["lat"], d["lon"]))
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
