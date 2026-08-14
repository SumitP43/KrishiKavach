import os
import pickle
import math
import json
import random
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import DBSCAN
from database import get_db_connection

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.pkl")

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculates the bearing (compass angle in degrees) from coordinate 1 to coordinate 2."""
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
    
    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    return bearing

def calculate_upwind_fires(target_district, districts, hotspots, wind_dir):
    """
    Computes the number of active fires upwind of the target district.
    A district is considered upwind if the bearing from it to the target district 
    is within 45 degrees of the direction the wind is blowing (wind_dir).
    """
    if not hotspots:
        return 0
        
    upwind_count = 0
    t_lat, t_lon = target_district['latitude'], target_district['longitude']
    
    for h in hotspots:
        # Distance from hotspot to target district (simple degree distance)
        dist = ((h['latitude'] - t_lat)**2 + (h['longitude'] - t_lon)**2)**0.5
        if dist < 0.1: # Skip very close fires (they count as local)
            continue
            
        # Angle from hotspot to target district
        bearing = calculate_bearing(h['latitude'], h['longitude'], t_lat, t_lon)
        
        # Wind direction indicates where wind is coming from.
        # So wind blowing from hotspot to target means the direction from hotspot to target 
        # aligns with the wind direction (e.g. NW winds blowing from NW to SE).
        # We check difference between wind_dir (direction coming from) and bearing (from hotspot to target)
        angle_diff = abs(wind_dir - bearing)
        angle_diff = min(angle_diff, 360 - angle_diff)
        
        if angle_diff <= 45.0: # Within 45 degrees of wind vector
            # Weight by distance (closer fires have higher impact)
            weight = 1.0 / (dist + 0.5)
            upwind_count += weight
            
    return round(upwind_count, 2)

def train_predictive_model():
    """Generates synthetic historical data for 3 seasons and trains a RandomForestClassifier."""
    print("Generating historical stubble burning dataset for model training...")
    
    np.random.seed(42)
    data = []
    
    # Generate 1000 simulated observations
    for _ in range(1000):
        local_fires = np.random.poisson(lam=1.5) if random.random() < 0.6 else np.random.poisson(lam=6.0)
        upwind_fires = np.random.uniform(0, 15) if random.random() < 0.5 else np.random.uniform(15, 60)
        wind_speed = np.random.uniform(3, 25) # km/h
        humidity = np.random.uniform(40, 95) # %
        current_aqi = np.random.uniform(80, 250) + local_fires * 15 + upwind_fires * 2
        
        # Risk factors determining the next 24-48hr AQI spike
        # Lower wind speed and higher humidity trap smoke, increasing risk
        # High upwind fires combined with wind blowing towards target increases risk
        transport_effect = upwind_fires * (15.0 / (wind_speed + 2.0)) * (humidity / 70.0)
        future_aqi = current_aqi * 0.8 + local_fires * 25 + transport_effect + np.random.normal(0, 15)
        future_aqi = min(max(future_aqi, 30), 500)
        
        # Risk label
        if future_aqi < 150:
            risk = 0 # Low
        elif future_aqi < 300:
            risk = 1 # Medium
        else:
            risk = 2 # High
            
        data.append([local_fires, upwind_fires, wind_speed, humidity, current_aqi, risk])
        
    df = pd.DataFrame(data, columns=['local_fires', 'upwind_fires', 'wind_speed', 'humidity', 'current_aqi', 'risk'])
    X = df.drop('risk', axis=1)
    y = df['risk']
    
    print("Training Random Forest Classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Save model
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump({
            'model': model,
            'feature_importances': model.feature_importances_.tolist(),
            'features': X.columns.tolist()
        }, f)
        
    print(f"Model trained successfully and saved to {MODEL_PATH}")
    print("Feature Importances:", dict(zip(X.columns, model.feature_importances_)))

def predict_district_risks():
    """Predicts next 24-48hr risk level for all districts using the database state."""
    # Ensure model is trained
    if not os.path.exists(MODEL_PATH):
        train_predictive_model()
        
    with open(MODEL_PATH, 'rb') as f:
        saved = pickle.load(f)
        model = saved['model']
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all districts
    cursor.execute("SELECT id, name, latitude, longitude, state FROM districts")
    districts = [dict(row) for row in cursor.fetchall()]
    
    # Get all active hotspots
    cursor.execute("SELECT latitude, longitude, confidence FROM hotspots")
    hotspots = [dict(row) for row in cursor.fetchall()]
    
    # Get current weather/AQI
    cursor.execute("""
    SELECT w.district_id, w.aqi, w.wind_speed, w.wind_dir, w.humidity 
    FROM weather_aqi w
    JOIN (SELECT district_id, MAX(timestamp) as max_t FROM weather_aqi GROUP BY district_id) latest
    ON w.district_id = latest.district_id AND w.timestamp = latest.max_t
    """)
    weather_map = {row['district_id']: dict(row) for row in cursor.fetchall()}
    
    predictions = []
    prediction_date = (np.datetime64('now') + np.timedelta64(24, 'h')).astype(str)
    
    # Clear old predictions
    cursor.execute("DELETE FROM predictions")
    
    for d in districts:
        d_id = d['id']
        w = weather_map.get(d_id)
        if not w:
            continue
            
        # Count local fires
        cursor.execute("SELECT COUNT(*) FROM hotspots WHERE district_id = ?", (d_id,))
        local_fires = cursor.fetchone()[0]
        
        # Calculate upwind fires based on wind direction
        upwind_fires = calculate_upwind_fires(d, districts, hotspots, w['wind_dir'])
        
        # Assemble feature vector
        features = [
            local_fires,
            upwind_fires,
            w['wind_speed'],
            w['humidity'],
            w['aqi']
        ]
        
        # Predict probability
        probs = model.predict_proba([features])[0]
        pred_class = np.argmax(probs)
        confidence = probs[pred_class]
        
        risk_labels = ['Low', 'Medium', 'High']
        risk_level = risk_labels[pred_class]
        
        features_json = json.dumps({
            'local_fires': local_fires,
            'upwind_fires': upwind_fires,
            'wind_speed': round(w['wind_speed'], 2),
            'wind_dir': round(w['wind_dir'], 2),
            'humidity': round(w['humidity'], 2),
            'current_aqi': w['aqi']
        })
        
        cursor.execute("""
        INSERT INTO predictions (district_id, prediction_date, risk_level, confidence, features)
        VALUES (?, ?, ?, ?, ?)
        """, (d_id, prediction_date, risk_level, confidence, features_json))
        
        predictions.append({
            'district_name': d['name'],
            'district_id': d_id,
            'risk_level': risk_level,
            'confidence': confidence,
            'features': json.loads(features_json)
        })
        
    conn.commit()
    conn.close()
    return predictions

def run_dbscan_clustering():
    """Runs DBSCAN on active hotspots to find active burning zone clusters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, latitude, longitude, confidence FROM hotspots")
    hotspots = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not hotspots or len(hotspots) < 2:
        return {'clusters': [], 'noise': hotspots}
        
    coords = np.array([[h['latitude'], h['longitude']] for h in hotspots])
    
    # DBSCAN: eps=0.15 is roughly 15km, min_samples=2
    db = DBSCAN(eps=0.15, min_samples=2).fit(coords)
    labels = db.labels_
    
    clusters = {}
    noise = []
    
    for i, h in enumerate(hotspots):
        label = labels[i]
        if label == -1:
            noise.append(h)
        else:
            if label not in clusters:
                clusters[label] = {
                    'cluster_id': int(label),
                    'hotspots': [],
                    'centroid': [0.0, 0.0],
                    'avg_confidence': 0.0
                }
            clusters[label]['hotspots'].append(h)
            
    # Calculate centroids and statistics for clusters
    for label, cluster in clusters.items():
        c_coords = np.array([[h['latitude'], h['longitude']] for h in cluster['hotspots']])
        cluster['centroid'] = c_coords.mean(axis=0).tolist()
        cluster['avg_confidence'] = float(np.mean([h['confidence'] for h in cluster['hotspots']]))
        cluster['fire_count'] = len(cluster['hotspots'])
        
    return {
        'clusters': list(clusters.values()),
        'noise': noise
    }

if __name__ == "__main__":
    train_predictive_model()
    predicts = predict_district_risks()
    print(f"Generated {len(predicts)} risk predictions.")
    c_res = run_dbscan_clustering()
    print(f"Identified {len(c_res['clusters'])} active fire clusters.")
