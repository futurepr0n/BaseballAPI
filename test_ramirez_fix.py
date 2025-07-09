#!/usr/bin/env python3
"""Test José Ramírez name matching fix"""

import requests
import json

def test_ramirez_api():
    """Test if José Ramírez is now found in the API"""
    
    print("Testing José Ramírez name matching fix...")
    
    # Use a real pitcher name
    payload = {
        "pitcher_name": "Hunter Brown",  # Use a real pitcher name
        "team": "CLE", 
        "max_results": 10
    }
    
    api_url = "http://localhost:8000/analyze/pitcher-vs-team"
    
    print(f"\n🔍 Testing team search for CLE (should include José Ramírez)...")
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            predictions = data.get('predictions', [])
            
            print(f"✅ API call successful! Found {len(predictions)} predictions")
            
            # Debug: Show the actual structure of the first prediction
            if predictions:
                print(f"🔍 First prediction structure:")
                first_pred = predictions[0]
                print(f"   Keys: {list(first_pred.keys())}")
                print(f"   Raw data: {first_pred}")
            
            # Look for any Ramirez variants in the predictions
            ramirez_found = False
            all_player_names = []
            
            for prediction in predictions:
                # Use correct field name from API response
                player_name = prediction.get('batter_name', '')
                all_player_names.append(player_name)
                
                if player_name and 'ramirez' in str(player_name).lower():
                    print(f"✅ Found {player_name} in predictions!")
                    print(f"   HR Score: {prediction.get('score', 'N/A')}")
                    print(f"   Confidence: {prediction.get('confidence', 'N/A')}")
                    print(f"   Hit Probability: {prediction.get('outcome_probabilities', {}).get('hit', 'N/A')}")
                    print(f"   HR Probability: {prediction.get('outcome_probabilities', {}).get('homerun', 'N/A')}")
                    print(f"   Team: {prediction.get('batter_team', 'N/A')}")
                    ramirez_found = True
                    break
            
            if not ramirez_found:
                print(f"❌ No Ramirez found in {len(predictions)} predictions")
                print(f"   All player names found: {all_player_names}")
                
                # Show sample of what we did find
                print(f"\n📋 Sample prediction data:")
                for i, pred in enumerate(predictions[:3]):
                    print(f"   [{i}]: {pred}")
                    
                # Check if any Cleveland players at all
                cle_players = [p for p in predictions if p.get('team') == 'CLE']
                print(f"\n🏟️ Cleveland players found: {len(cle_players)}")
                if cle_players:
                    print(f"   CLE sample: {cle_players[0]}")
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_ramirez_api()