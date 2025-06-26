#!/usr/bin/env python3
"""
Simple test to debug the lookup chain issue.
"""

import requests
import json

def test_simple_case():
    """Test a simple case that should work"""
    
    # Test José Alvarado vs PHI (this was working in our previous test)
    payload = {
        "pitcher_name": "José Alvarado",
        "team": "PHI",
        "sort_by": "score",
        "min_score": 0,
        "include_confidence": True,
        "max_results": 3
    }
    
    print("🎯 Testing José Alvarado vs PHI")
    
    try:
        response = requests.post(
            "http://localhost:8000/analyze/pitcher-vs-team",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Success: {data.get('success')}")
            
            predictions = data.get('predictions', [])
            print(f"📊 Predictions: {len(predictions)}")
            
            if predictions:
                first_pred = predictions[0]
                print(f"\n🔍 First Prediction Analysis:")
                print(f"   Player name: {first_pred.get('player_name', 'Unknown')}")
                print(f"   Score: {first_pred.get('score', 0)}")
                print(f"   Confidence: {first_pred.get('confidence', 0)}")
                
                # Check recent performance structure
                recent_perf = first_pred.get('recent_performance', {})
                print(f"\n📈 Recent Performance Structure:")
                print(f"   Keys: {list(recent_perf.keys())}")
                
                if 'last_7_games' in recent_perf:
                    games = recent_perf['last_7_games']
                    print(f"   Last 7 games: {len(games)} games found")
                    if games:
                        print(f"   Sample game: {games[0]}")
                else:
                    print(f"   ❌ No 'last_7_games' key found")
                
                # Check if any recent performance data exists
                if recent_perf:
                    print(f"   Recent performance data: {recent_perf}")
                else:
                    print(f"   ❌ No recent performance data")
                
                # Look for data_source indicators
                if 'data_source' in recent_perf:
                    print(f"   Data source: {recent_perf['data_source']}")
        
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"   Error: {response.text}")
    
    except Exception as e:
        print(f"❌ Request error: {e}")

def test_pitcher_search():
    """Test if we can find any pitchers at all"""
    
    test_pitchers = [
        "José Alvarado",
        "Jose Alvarado",  # Without accent
        "Blake Snell",
        "Gerrit Cole",
        "Spencer Strider",
        "Dylan Cease",
        "Corbin Burnes"
    ]
    
    print(f"\n🔍 Testing Pitcher Search:")
    
    for pitcher in test_pitchers:
        payload = {"name": pitcher, "player_type": "pitcher"}
        
        try:
            response = requests.post(
                "http://localhost:8000/players/search",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                found = data.get('found', False)
                
                if found:
                    player = data.get('player', {})
                    print(f"   ✅ {pitcher} → Found: {player.get('name')} ({player.get('team')})")
                else:
                    suggestions = data.get('suggestions', [])
                    if suggestions:
                        print(f"   ⚠️  {pitcher} → Not found, but {len(suggestions)} suggestions")
                    else:
                        print(f"   ❌ {pitcher} → Not found, no suggestions")
            else:
                print(f"   ❌ {pitcher} → Search error: {response.status_code}")
        
        except Exception as e:
            print(f"   ❌ {pitcher} → Error: {e}")

if __name__ == "__main__":
    test_simple_case()
    test_pitcher_search()