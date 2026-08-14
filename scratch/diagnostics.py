import urllib.request
import json
import sys

API_BASE = "http://localhost:8000"
endpoints = [
    "/api/districts",
    "/api/hotspots",
    "/api/predictions",
    "/api/farmers",
    "/api/advisories"
]

def run_diagnostics():
    print("==================================================")
    print("           KRISHIKAVACH DIAGNOSTICS SYSTEM         ")
    print("==================================================")
    
    all_healthy = True
    
    for ep in endpoints:
        url = f"{API_BASE}{ep}"
        print(f"Testing {url: <35} ... ", end="")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'DiagnosticsClient'})
            with urllib.request.urlopen(req, timeout=3) as response:
                status = response.getcode()
                body = response.read().decode('utf-8')
                data = json.loads(body)
                
                if status == 200:
                    print("[ OK ]")
                    # Print brief summary depending on endpoint
                    if ep == "/api/districts":
                        print(f"   -> Loaded: {len(data)} districts")
                    elif ep == "/api/hotspots":
                        hotspots = data.get("hotspots", [])
                        clusters = data.get("clusters", [])
                        print(f"   -> Loaded: {len(hotspots)} hotspots grouped in {len(clusters)} DBSCAN clusters")
                    elif ep == "/api/predictions":
                        print(f"   -> Forecasts: {len(data)} district risk levels computed")
                    elif ep == "/api/farmers":
                        print(f"   -> Farmers: {len(data)} registered in system")
                    elif ep == "/api/advisories":
                        print(f"   -> Advisories: {len(data)} alerts logged in dispatch history")
                else:
                    print(f"[ FAILED: HTTP STATUS {status} ]")
                    all_healthy = False
        except Exception as e:
            print(f"[ FAILED: {str(e)} ]")
            all_healthy = False
            
    print("==================================================")
    if all_healthy:
        print("RESULT: All backend modules are HEALTHY and online!")
        sys.exit(0)
    else:
        print("RESULT: Some endpoints failed verification. Check logs.")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostics()
