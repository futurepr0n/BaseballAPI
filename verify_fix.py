#!/usr/bin/env python3
"""Verify that the fix is working for all predictions"""

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

print("Verifying field mapping fix...")
print("-" * 80)

try:
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        
        if "predictions" in data and len(data["predictions"]) > 0:
            print(f"✅ Got {len(data['predictions'])} predictions\n")
            
            # Check all predictions
            all_have_trend_dir = True
            all_have_ab_due = True
            
            for i, pred in enumerate(data["predictions"]):
                player = pred.get('batter_name', 'Unknown')
                
                # Check recent_trend_dir
                has_trend_dir = 'recent_trend_dir' in pred
                trend_in_obj = (
                    'recent_N_games_raw_data' in pred and 
                    'trends_summary_obj' in pred['recent_N_games_raw_data'] and
                    'trend_direction' in pred['recent_N_games_raw_data']['trends_summary_obj']
                )
                
                # Check ab_due
                has_ab_due = 'ab_due' in pred
                ab_in_details = (
                    'details' in pred and 
                    'due_for_hr_ab_raw_score' in pred['details']
                )
                
                if not has_trend_dir or not trend_in_obj:
                    all_have_trend_dir = False
                    print(f"❌ {player}: Missing trend_dir (top: {has_trend_dir}, obj: {trend_in_obj})")
                
                if not has_ab_due or not ab_in_details:
                    all_have_ab_due = False
                    print(f"❌ {player}: Missing ab_due (top: {has_ab_due}, details: {ab_in_details})")
                
                if i < 3:  # Show first 3 predictions in detail
                    trend_val = pred.get('recent_trend_dir', 'MISSING')
                    ab_val = pred.get('ab_due', 'MISSING')
                    print(f"Player {i+1}: {player}")
                    print(f"  - recent_trend_dir: {trend_val}")
                    print(f"  - ab_due: {ab_val}")
            
            print("\n" + "=" * 80)
            print("SUMMARY:")
            print(f"✅ All predictions have recent_trend_dir: {all_have_trend_dir}")
            print(f"✅ All predictions have ab_due: {all_have_ab_due}")
            
            if all_have_trend_dir and all_have_ab_due:
                print("\n🎉 SUCCESS! All fields are properly mapped.")
                print("PinheadsPlayhouse should now show correct values for:")
                print("  - Recent Trend Dir column")
                print("  - AB Due column")
            else:
                print("\n⚠️  Some predictions still missing fields")
                
        else:
            print("❌ No predictions in response")
    else:
        print(f"❌ API returned status code: {response.status_code}")
        
except Exception as e:
    print(f"❌ Error: {e}")