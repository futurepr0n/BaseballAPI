#!/usr/bin/env python3
"""Test API response structure for Recent Trend Dir and AB Due fields"""

import requests
import json

# Test the API endpoint
url = "http://localhost:8000/analyze/pitcher-vs-team"
payload = {
    "pitcher_name": "Hunter Brown",
    "team": "SEA",
    "sort_by": "score",
    "min_score": 0,
    "include_confidence": True
}

print("Testing API response structure...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("-" * 80)

try:
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        
        # Check if we have predictions
        if "predictions" in data and len(data["predictions"]) > 0:
            print(f"✅ Got {len(data['predictions'])} predictions")
            
            # Analyze first prediction structure
            first_pred = data["predictions"][0]
            print(f"\n📊 First prediction for: {first_pred.get('batter_name', 'Unknown')}")
            print("-" * 80)
            
            # Check for the problematic fields
            print("\n🔍 CHECKING FIELD STRUCTURE:")
            
            # Check recent_trend_dir field
            print("\n1. Recent Trend Dir field:")
            if "recent_trend_dir" in first_pred:
                print(f"   ✅ recent_trend_dir: {first_pred['recent_trend_dir']}")
            else:
                print("   ❌ recent_trend_dir: NOT FOUND in top level")
            
            # Check in recent_N_games_raw_data
            if "recent_N_games_raw_data" in first_pred:
                recent_data = first_pred["recent_N_games_raw_data"]
                print(f"   📦 recent_N_games_raw_data exists: {type(recent_data)}")
                
                if isinstance(recent_data, dict) and "trends_summary_obj" in recent_data:
                    trends = recent_data["trends_summary_obj"]
                    print(f"      📦 trends_summary_obj exists: {type(trends)}")
                    
                    if isinstance(trends, dict) and "trend_direction" in trends:
                        print(f"      ✅ trend_direction in trends_summary_obj: {trends['trend_direction']}")
                    else:
                        print(f"      ❌ trend_direction NOT in trends_summary_obj")
                        print(f"      Available keys: {list(trends.keys()) if isinstance(trends, dict) else 'Not a dict'}")
            
            # Check ab_due field
            print("\n2. AB Due field:")
            if "ab_due" in first_pred:
                print(f"   ✅ ab_due: {first_pred['ab_due']}")
            else:
                print("   ❌ ab_due: NOT FOUND in top level")
            
            # Check in details
            if "details" in first_pred:
                details = first_pred["details"]
                print(f"   📦 details exists: {type(details)}")
                
                if isinstance(details, dict) and "due_for_hr_ab_raw_score" in details:
                    print(f"      ✅ due_for_hr_ab_raw_score in details: {details['due_for_hr_ab_raw_score']}")
                else:
                    print(f"      ❌ due_for_hr_ab_raw_score NOT in details")
                    print(f"      Available keys: {list(details.keys()) if isinstance(details, dict) else 'Not a dict'}")
            
            # Print full structure for debugging
            print("\n📋 FULL PREDICTION STRUCTURE (first 5 fields):")
            for i, (key, value) in enumerate(first_pred.items()):
                if i < 5:
                    value_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                    print(f"   {key}: {value_str}")
            
            print(f"\n📋 ALL TOP-LEVEL KEYS ({len(first_pred)} total):")
            print(f"   {sorted(first_pred.keys())}")
            
        else:
            print("❌ No predictions in response")
    else:
        print(f"❌ API returned status code: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error testing API: {e}")