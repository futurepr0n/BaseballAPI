#!/usr/bin/env python3
"""
Test all endpoints to verify they're working
"""

import requests
import json

def test_all_endpoints():
    base_url = "http://localhost:8000"
    
    print("🧪 Testing All API Endpoints...")
    
    endpoints_to_test = [
        ("GET", "/health", None),
        ("GET", "/data/status", None),
        ("GET", "/sort-options", None),
        ("GET", "/analyze/data-quality", None),
        ("POST", "/players/search", {"name": "MacKenzie Gore", "player_type": "pitcher"}),
        ("POST", "/analyze/pitcher-vs-team", {
            "pitcher_name": "MacKenzie Gore",
            "team": "SEA",
            "include_confidence": True
        })
    ]
    
    for method, endpoint, payload in endpoints_to_test:
        print(f"\n🔍 Testing {method} {endpoint}")
        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
            else:
                response = requests.post(
                    f"{base_url}{endpoint}",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload) if payload else None,
                    timeout=10
                )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if endpoint == "/sort-options":
                    print(f"   Sort options count: {len(data.get('options', []))}")
                elif endpoint == "/data/status":
                    print(f"   Initialization: {data.get('initialization_status')}")
                elif endpoint == "/analyze/pitcher-vs-team":
                    print(f"   Predictions: {len(data.get('predictions', []))}")
                    if data.get('predictions'):
                        print(f"   First player: {data['predictions'][0].get('batter_name', 'N/A')}")
                else:
                    print(f"   Response keys: {list(data.keys())}")
            else:
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"   Failed: {e}")
    
    print("\n✅ Endpoint testing complete!")

if __name__ == "__main__":
    test_all_endpoints()