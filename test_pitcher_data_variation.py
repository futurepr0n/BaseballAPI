#!/usr/bin/env python3
"""
Test script to verify that different pitchers return different stats
This will help diagnose the issue where all pitchers show identical ERA, WHIP, etc.
"""

import requests
import json

API_BASE = "http://localhost:8000"

def test_pitcher_variation():
    """Test multiple pitchers to see if they return different stats"""
    
    pitchers_to_test = [
        {"pitcher_name": "Merrill Kelly", "team": "COL"},
        {"pitcher_name": "Carson Palmquist", "team": "ARI"},
        {"pitcher_name": "Noah Cameron", "team": "SD"},
        {"pitcher_name": "Dylan Cease", "team": "KC"},
        {"pitcher_name": "Griffin Canning", "team": "PHI"}
    ]
    
    print("🔍 Testing Pitcher Data Variation in BaseballAPI")
    print("=" * 60)
    
    pitcher_stats = {}
    
    for i, matchup in enumerate(pitchers_to_test, 1):
        print(f"\n{i}. Testing {matchup['pitcher_name']} vs {matchup['team']}")
        
        url = f"{API_BASE}/analyze/pitcher-vs-team"
        data = {
            "pitcher_name": matchup["pitcher_name"],
            "team": matchup["team"],
            "sort_by": "score",
            "max_results": 1,
            "include_confidence": True
        }
        
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            
            if result.get('predictions') and len(result['predictions']) > 0:
                pred = result['predictions'][0]
                
                # Extract pitcher-specific data
                pitcher_data = {
                    'pitcher_name': pred.get('pitcher_name'),
                    'pitcher_era': pred.get('pitcher_era'),
                    'pitcher_whip': pred.get('pitcher_whip'),
                    'pitcher_k_per_game': pred.get('pitcher_k_per_game', 0),
                    'pitcher_home_hr_total': pred.get('pitcher_home_hr_total', 0),
                    'pitcher_home_games': pred.get('pitcher_home_games', 0),
                    'ev_matchup_score': pred.get('ev_matchup_score', 0),
                    'requested_pitcher': matchup["pitcher_name"]
                }
                
                # Store for comparison
                pitcher_stats[matchup["pitcher_name"]] = pitcher_data
                
                print(f"   ✅ Response received")
                print(f"   Returned pitcher: {pitcher_data['pitcher_name']}")
                print(f"   ERA: {pitcher_data['pitcher_era']}")
                print(f"   WHIP: {pitcher_data['pitcher_whip']}")
                print(f"   K/Game: {pitcher_data['pitcher_k_per_game']}")
                print(f"   EV Matchup: {pitcher_data['ev_matchup_score']}")
                print(f"   Home HR Total: {pitcher_data['pitcher_home_hr_total']}")
                print(f"   Name Match: {pitcher_data['pitcher_name'] == matchup['pitcher_name']}")
                
            else:
                print(f"   ❌ No predictions returned")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Analyze results
    print("\n" + "=" * 60)
    print("🔍 ANALYSIS RESULTS")
    print("=" * 60)
    
    if len(pitcher_stats) < 2:
        print("❌ Not enough data to compare")
        return
    
    # Check for identical values
    fields_to_check = ['pitcher_era', 'pitcher_whip', 'pitcher_k_per_game', 'ev_matchup_score']
    
    for field in fields_to_check:
        values = [stats[field] for stats in pitcher_stats.values() if stats[field] is not None]
        unique_values = set(values)
        
        print(f"\n{field.upper()}:")
        print(f"  Total values: {len(values)}")
        print(f"  Unique values: {len(unique_values)}")
        print(f"  Values: {list(unique_values)}")
        
        if len(unique_values) == 1 and len(values) > 1:
            print(f"  🚨 ISSUE: All pitchers have identical {field} ({list(unique_values)[0]})")
        elif len(unique_values) == len(values):
            print(f"  ✅ GOOD: All pitchers have unique {field}")
        else:
            print(f"  ⚠️ MIXED: Some pitchers share {field} values")
    
    # Show pitcher name matching
    print(f"\nPITCHER NAME MATCHING:")
    for requested, stats in pitcher_stats.items():
        returned = stats['pitcher_name']
        match = returned == requested
        print(f"  {requested} → {returned} ({'✅' if match else '❌'})")
    
    print(f"\n📊 SUMMARY:")
    print(f"  Pitchers tested: {len(pitcher_stats)}")
    
    # Calculate how many fields have variation
    varying_fields = 0
    for field in fields_to_check:
        values = [stats[field] for stats in pitcher_stats.values() if stats[field] is not None]
        if len(set(values)) > 1:
            varying_fields += 1
    
    print(f"  Fields with variation: {varying_fields}/{len(fields_to_check)}")
    
    if varying_fields == 0:
        print(f"  🚨 CRITICAL ISSUE: No pitcher stats vary between different pitchers!")
        print(f"  This explains why all pitcher columns show the same values in the UI.")
    elif varying_fields == len(fields_to_check):
        print(f"  ✅ GOOD: All pitcher stats vary correctly")
    else:
        print(f"  ⚠️ PARTIAL ISSUE: Some pitcher stats don't vary")

if __name__ == "__main__":
    test_pitcher_variation()