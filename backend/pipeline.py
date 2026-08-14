import urllib.request
import csv
import io
import json
import random
import os
from datetime import datetime, timedelta
import sqlite3
from database import get_db_connection, init_db

# Bounding box for Punjab, Haryana, and Delhi/NCR
# Min Lat: 27.5, Max Lat: 33.0
# Min Lon: 73.5, Max Lon: 78.5
LAT_MIN, LAT_MAX = 27.5, 33.0
LON_MIN, LON_MAX = 73.5, 78.5

# NASA FIRMS South Asia 24h CSV URL
NASA_FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/VIIRS_SNPP_NRT_South_Asia_24h.csv"

def fetch_live_hotspots():
    """Fetches near-real-time active fires from NASA FIRMS and filters for Punjab/Haryana/NCR."""
    print("Fetching live hotspots from NASA FIRMS...")
    hotspots = []
    try:
        req = urllib.request.Request(
            NASA_FIRMS_URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            csv_data = response.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(csv_data))
            for row in reader:
                lat = float(row['latitude'])
                lon = float(row['longitude'])
                # Filter for our bounding box
                if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
                    # VIIRS NRT has confidence as low/nominal/high, map to numeric
                    conf_str = row.get('confidence', 'n').lower()
                    confidence = 80.0 if conf_str == 'h' else (50.0 if conf_str == 'n' else 20.0)
                    hotspots.append({
                        'latitude': lat,
                        'longitude': lon,
                        'confidence': confidence,
                        'acq_date': row['acq_date'],
                        'acq_time': row['acq_time']
                    })
        print(f"Successfully fetched {len(hotspots)} live hotspots in target region.")
    except Exception as e:
        print(f"Error fetching NASA FIRMS data: {e}. Falling back to simulation.")
    return hotspots

def fetch_open_meteo_weather_aqi(lat, lon):
    """Fetches weather and AQI forecast from Open-Meteo for a given coordinate."""
    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=relative_humidity_2m,wind_speed_10m,wind_direction_10m&forecast_days=1"
    aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=pm2_5,pm10,us_aqi&forecast_days=1"
    
    data = {
        'wind_speed': 10.0,
        'wind_dir': 180.0,
        'humidity': 60.0,
        'aqi': 80,
        'pm25': 25.0,
        'pm10': 50.0
    }
    
    try:
        # Fetch weather
        with urllib.request.urlopen(weather_url, timeout=5) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            if 'hourly' in res_json:
                # Take current hour or first value
                data['humidity'] = res_json['hourly']['relative_humidity_2m'][0]
                data['wind_speed'] = res_json['hourly']['wind_speed_10m'][0]
                data['wind_dir'] = res_json['hourly']['wind_direction_10m'][0]
                
        # Fetch AQI
        with urllib.request.urlopen(aqi_url, timeout=5) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            if 'hourly' in res_json:
                data['aqi'] = res_json['hourly']['us_aqi'][0] or 50
                data['pm25'] = res_json['hourly']['pm2_5'][0] or 15.0
                data['pm10'] = res_json['hourly']['pm10'][0] or 30.0
    except Exception as e:
        print(f"Error fetching weather/AQI from Open-Meteo: {e}")
        
    return data

def get_closest_district(lat, lon, districts):
    """Finds the closest district by Euclidean distance."""
    closest_dist = float('inf')
    closest_id = None
    for d in districts:
        dist = ((d['latitude'] - lat)**2 + (d['longitude'] - lon)**2)**0.5
        if dist < closest_dist:
            closest_dist = dist
            closest_id = d['id']
    # Threshold check: within ~80km
    if closest_dist < 0.8:
        return closest_id
    return None

def run_data_pipeline(simulate=False):
    """Runs the data ingestion and storage pipeline."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Get districts
    cursor.execute("SELECT id, name, latitude, longitude, state FROM districts")
    districts = [dict(row) for row in cursor.fetchall()]
    
    if not districts:
        print("No districts found. Reinitializing DB.")
        init_db()
        cursor.execute("SELECT id, name, latitude, longitude, state FROM districts")
        districts = [dict(row) for row in cursor.fetchall()]
        
    print(f"Processing data for {len(districts)} districts...")
    
    timestamp = datetime.now().isoformat()
    
    # 2. Get Hotspots
    hotspots = []
    if not simulate:
        hotspots = fetch_live_hotspots()
        
    # If no live hotspots (common outside stubble season) or if simulation requested
    if simulate or len(hotspots) == 0:
        print("No live hotspots found or simulating. Generating realistic mock fires...")
        # Generate active fires primarily in Punjab/Haryana farming districts
        for d in districts:
            if d['state'] in ['Punjab', 'Haryana']:
                # Probability of active fire: Ludhiana, Sangrur, Amritsar, Karnal are hotspots
                fire_prob = 0.7 if d['name'] in ['Sangrur', 'Amritsar', 'Ludhiana', 'Bathinda', 'Karnal'] else 0.3
                if random.random() < fire_prob:
                    # Generate 1 to 5 fires around the district centroid
                    num_fires = random.randint(1, 5)
                    for _ in range(num_fires):
                        hotspots.append({
                            'latitude': d['latitude'] + random.uniform(-0.15, 0.15),
                            'longitude': d['longitude'] + random.uniform(-0.15, 0.15),
                            'confidence': random.uniform(50, 100),
                            'acq_date': datetime.now().strftime("%Y-%m-%d"),
                            'acq_time': datetime.now().strftime("%H%M")
                        })
        print(f"Generated {len(hotspots)} simulated hotspots.")
        
    # Clear old hotspots to avoid map clutter in demo
    cursor.execute("DELETE FROM hotspots")
    
    # Insert hotspots
    for h in hotspots:
        d_id = get_closest_district(h['latitude'], h['longitude'], districts)
        cursor.execute("""
        INSERT INTO hotspots (latitude, longitude, confidence, acq_date, acq_time, district_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (h['latitude'], h['longitude'], h['confidence'], h['acq_date'], h['acq_time'], d_id))
        
    # 3. Get Weather & AQI for each district
    # Clear old weather records to keep history brief
    cursor.execute("DELETE FROM weather_aqi")
    
    for d in districts:
        if simulate:
            # Generate typical stubble-burning weather conditions
            # Low wind speed, North-Westerly winds (approx 290-340 degrees) blowing smoke towards NCR
            is_punjab_haryana = d['state'] in ['Punjab', 'Haryana']
            
            # Count fires in this district
            local_fires = sum(1 for h in hotspots if get_closest_district(h['latitude'], h['longitude'], districts) == d['id'])
            
            humidity = random.uniform(65, 85) # High morning humidity/fog traps particles
            wind_speed = random.uniform(5, 12) # Low wind speed prevents dispersion
            # Wind from North-West (315 degrees is NW)
            wind_dir = random.uniform(300, 330)
            
            # Calculate simulated AQI
            if is_punjab_haryana:
                # Fire density directly impacts local AQI
                base_aqi = 120 + local_fires * 45
                pm25 = local_fires * 35 + random.uniform(40, 80)
            else:
                # Delhi/NCR: Affected by wind direction and cumulative fires upwind
                upwind_fires = len(hotspots)
                # If wind is NW (300-340), smoke blows towards Delhi
                wind_factor = 1.2 if (300 <= wind_dir <= 340 or 0 <= wind_dir <= 30) else 0.4
                base_aqi = 150 + (upwind_fires * 3.5) * wind_factor
                pm25 = (upwind_fires * 2.2) * wind_factor + random.uniform(50, 100)
                
            aqi = int(min(base_aqi, 500)) # Cap at 500 (Severe/Hazardous)
            pm10 = pm25 * 1.6
            w_data = {
                'wind_speed': wind_speed,
                'wind_dir': wind_dir,
                'humidity': humidity,
                'aqi': aqi,
                'pm25': pm25,
                'pm10': pm10
            }
        else:
            # Fetch live open-meteo weather and AQI
            w_data = fetch_open_meteo_weather_aqi(d['latitude'], d['longitude'])
            
        cursor.execute("""
        INSERT INTO weather_aqi (district_id, timestamp, aqi, pm25, pm10, wind_speed, wind_dir, humidity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (d['id'], timestamp, w_data['aqi'], w_data['pm25'], w_data['pm10'], 
              w_data['wind_speed'], w_data['wind_dir'], w_data['humidity']))
        
    conn.commit()
    conn.close()
    print("Pipeline run completed. Database updated.")

if __name__ == "__main__":
    # Run the pipeline with simulation by default to ensure we have data
    run_data_pipeline(simulate=True)
