import sqlite3
import os
import sys
from database import get_db_connection, init_db
from pipeline import run_data_pipeline
from ml_model import predict_district_risks

def reset_all():
    print("Resetting database...")
    init_db() # Ensure tables exist
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Clear registrations and advisories
        cursor.execute("DELETE FROM advisories")
        cursor.execute("DELETE FROM farmers")
        
        # Clear transactional weather/hotspots/predictions
        cursor.execute("DELETE FROM hotspots")
        cursor.execute("DELETE FROM weather_aqi")
        cursor.execute("DELETE FROM predictions")
        conn.commit()
        print("Registrations, advisories, and metrics cleared.")
    except Exception as e:
        print(f"Error clearing tables: {e}")
        conn.rollback()
    finally:
        conn.close()

    # Re-run pipeline and prediction layer to build a fresh simulation base
    try:
        print("Generating fresh base data (simulation mode)...")
        run_data_pipeline(simulate=True)
        predict_district_risks()
        print("Fresh database state initialized successfully.")
    except Exception as e:
        print(f"Error re-running base pipeline: {e}")

if __name__ == "__main__":
    reset_all()
