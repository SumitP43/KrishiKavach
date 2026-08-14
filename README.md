# KrishiKavach (कृषिकवच) - Stubble Burning Early-Warning & Farmer Advisory System

A complete working prototype designed for the **Smart India Hackathon (SIH)**. This system predicts high-risk burning zones 24-48 hours in advance using meteorological forecasts and spatial active fire clustering, and connects flagged farmers directly to residue management resources via bilingual SMS alerts.

---

## 📝 SIH Submission: Problem Statement

> **Stubble burning in Punjab, Haryana, and Delhi/NCR** leads to severe, toxic Air Quality Index (AQI) spikes (450+ Severe) every October-November. Existing systems only flag fires after they've started, leaving authorities in a reactive state and offering no assistance to farmers trying to avoid burning. **KrishiKavach** solves this by predicting high-risk burning zones 24-48 hours in advance using spatial DBSCAN clustering on NASA FIRMS active fire datasets combined with wind vectors and humidity forecasts. Upon identifying a high-risk district, the system automatically translates predictions into direct bilingual (Hindi/English) SMS advisories sent to local farmers. These alerts list contact numbers for nearest government-subsidised Happy Seeder rental centers and residue buyback cooperatives, closing the loop between warning, detection, and grassroots intervention.

---

## 🛠️ Tech Stack & Folder Structure

*   **Backend:** Python FastAPI, SQLite, Scikit-learn (Random Forest, DBSCAN), APScheduler.
*   **Frontend:** React (Vite), Leaflet (React-Leaflet), Lucide Icons, Custom Glassmorphic CSS.
*   **APIs:** NASA FIRMS Active Fire Feed (NRT), Open-Meteo Weather & Air Quality APIs (free, public).

```
SIH/
├── backend/
│   ├── main.py          # FastAPI application server & endpoints
│   ├── database.py      # SQLite schema creation & static data
│   ├── pipeline.py      # Data ingestion from NASA FIRMS & Open-Meteo
│   ├── ml_model.py      # ML classifier training, DBSCAN & prediction
│   └── model.pkl        # Trained Random Forest classifier
├── data/
│   └── system.db        # SQLite database (auto-generated)
├── frontend/
│   ├── src/
│   │   ├── App.jsx      # React Dashboard and state
│   │   ├── index.css    # Modern custom styling
│   │   └── main.jsx     # App mounting entry point
│   ├── package.json     # Node project config
│   └── vite.config.js
├── README.md            # Setup, guide, & disclosures
└── pitch_deck.md        # Outline for judges pitch presentation
```

---

## 🚀 Setup & Running Locally

### Prerequisites
*   Python 3.8+
*   Node.js v18+

### Step 1: Set up the Backend
1.  Navigate to the backend directory (or stay in root and run backend scripts):
    ```bash
    # Install Python requirements
    pip install scikit-learn numpy pandas fastapi uvicorn apscheduler pydantic twilio
    ```
2.  Initialize the database and train the model:
    ```bash
    python backend/database.py
    python backend/ml_model.py
    ```
3.  Start the FastAPI Server:
    ```bash
    python backend/main.py
    ```
    The API will start running at `http://localhost:8000`.

### Step 2: Set up the Frontend
1.  Open a new terminal window, navigate to the `frontend` folder:
    ```bash
    cd frontend
    # Install dependencies
    npm install
    # Run the Vite development server
    npm run dev
    ```
2.  Open your browser and navigate to `http://localhost:5173`.

---

## 📊 Live vs. Mocked Components (Judge Transparency)

| Component | Status | Source / Mechanism |
| :--- | :--- | :--- |
| **NASA FIRMS Hotspots** | **REAL** | Pulled live from NASA FIRMS Suomi-NPP VIIRS 24h CSV feed, filtered to Punjab, Haryana, and NCR bounding box. |
| **Weather & AQI** | **REAL** | Pulled live from Open-Meteo Air Quality & weather forecasts for each district's centroid coordinates. |
| **ML Predictions** | **REAL** | A Random Forest Classifier trained on simulated seasonal datasets (local fires, wind speed/direction, humidity, baseline AQI) predicting 24-48h risk. DBSCAN clustering runs live on active hotspot coordinates. |
| **Farmer Registry** | **DEMO** | Uses a web registration form on the dashboard to populate a local SQLite database table (simulating a department registry). |
| **Bilingual Advisories** | **REAL** | Generated automatically in Hindi or English (based on selected preference) when a district prediction crosses the "Medium/High" threshold. |
| **SMS Gateway** | **SIMULATED** | Logged visually in a live scrolling advisory panel on the dashboard interface. Optionally supports real SMS dispatching via Twilio by setting the environment variables: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`. |
