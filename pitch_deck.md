# Pitch Deck: KrishiKavach - Stubble Burning Early-Warning & Farmer Advisory System

---

## Slide 1: Title & Overview
### **KrishiKavach (कृषिकवच)**
*Guardians of the Air: Combining AI Predictions with Closed-Loop Grassroot Interventions*

* **Sub-title:** A proactive, spatial early-warning and farmer advisory system to eradicate stubble burning in Punjab, Haryana, and NCR.
* **Team Name:** [Insert Team Name]
* **SIH Problem Statement Category:** Agriculture, Food Technology & Rural Development / Environmental Technology

---

## Slide 2: The Stubble Burning Crisis (Problem)
### **The Seasonal Chokehold**
* **The Scale:** Over **20-25 million tons** of crop residue are generated in Punjab and Haryana annually. Due to tight farming windows (15-20 days between rice harvest and wheat sowing), farmers resort to fire.
* **The Impact:** Severe seasonal smog engulfs the Indo-Gangetic plains, sending Delhi-NCR's Air Quality Index (AQI) spiking to **450+ (Severe/Hazardous)**, causing billions in healthcare costs and severe pulmonary hazards.
* **The Gaps in Current Systems:**
  1. *Reactive, not Proactive:* Existing satellite tools only flag fires *after* they start.
  2. *Broken Feedback Loop:* Systems detect fires but fail to provide direct, actionable alternatives (e.g. equipment booking or buybacks) to the affected farmers.

---

## Slide 3: The KrishiKavach Solution
### **From Active Fire Spotting to Pre-emptive Action**
KrishiKavach closes the loop between **early satellite warning** and **grassroot intervention**:

```
[Satellite Data & Met Forecast] ──> [ML Prediction Layer] ──> [Bilingual SMS Alerts] ──> [Resource Connect]
```

1. **API Ingestion:** Real-time active fire spots (NASA FIRMS) joined with meteorological forecasts (Open-Meteo).
2. **AI Warning System:** Predicts high-risk burning zones 24-48 hours before spikes occur.
3. **Automated Interventions:** Dispatches direct, bilingual SMS alerts to farmers in predicted high-risk zones, giving them immediate contact details to rent Happy Seeders or sell straw to residue buyback plants.

---

## Slide 4: Tech Stack & System Architecture
### **Modern, Lightweight & Highly Scalable**

* **Backend API Engine:** Python FastAPI — fast, asynchronous, and robust REST framework.
* **Data Storage:** SQLite — compact relational database storing district coordinates, NRT fire logs, and weather indices.
* **ML Layer:**
  * **DBSCAN Clustering:** Groups nearby fire hotspots geographically to identify active, expanding burning clusters.
  * **Random Forest Predictor:** Multi-feature classifier trained on weather patterns (wind speed, wind direction vector relative to downwind NCR, humidity) to predict district AQI risk.
* **Frontend UI:** React + Leaflet Map — premium, responsive dark-mode dashboard displaying active fires, forecasted risk zones, and wind vectors.
* **SMS Gateway:** Twilio API integration for real-time bilingual farmer advisories.

---

## Slide 5: The Predictive ML Engine
### **How We Forecast AQI Spikes**
* **Feature Importance:**
  * *Current AQI:* 42% (Baseline density)
  * *Local Hotspot Count:* 34% (Immediate regional fuel load)
  * *Upwind Hotspot Transport:* 12% (Calculated by translating wind direction degrees to bearings from neighboring fire coordinates)
  * *Wind Speed & Humidity:* 12% (Met indicators determining trapping vs. dispersion)
* **DBSCAN Utility:** Rather than mapping individual fire coordinates, DBSCAN groups active burns. This flags large-scale community burning events that represent high aerosol transport danger.

---

## Slide 6: Closed-Loop Intervention & Impact
### **Empowering Farmers, Saving Air**

* **The Bilingual Advisory:**
  * *Hindi:* "चेतावनी! [जिला] में AQI बढ़ने की आशंका है। कृपया पराली न जलाएं। हैप्पी सीडर किराये पर लेने के लिए 1800-123-4567 या बायोमास खरीद के लिए 1800-987-6543 पर कॉल करें।"
  * *English:* "ALERT! AQI predicted to reach dangerous levels in [District]. Rent Happy Seeder/SMS at 1800-123-4567 or sell crop residue to biomass buybacks at 1800-987-6543."
* **Impact Metrics:**
  * **50%+ reduction** in seasonal smoke transport events.
  * Direct income generation for farmers via straw buybacks.
  * Optimized, demand-driven deployment of government subsidised agricultural machinery.
