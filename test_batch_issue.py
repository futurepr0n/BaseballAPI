#!/usr/bin/env python3
"""
Test script to compare single vs batch analysis API responses
to identify why batch mode returns incomplete data
"""

import requests
import json
import sys

API_BASE = "http://localhost:8000"

def test_single_analysis():
    """Test single pitcher vs team analysis"""
    print("🔍 Testing Single Analysis...")
    
    url = f"{API_BASE}/analyze/pitcher-vs-team"
    data = {
        "pitcher_name": "MacKenzie Gore",
        "team": "SEA",
        "sort_by": "score",
        "include_confidence": True
    }
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        
        if result.get('predictions'):
            first_pred = result['predictions'][0]
            print(f"✅ Single Analysis Success: {len(result['predictions'])} predictions")
            print(f"Player: {first_pred.get('batter_name', 'N/A')}")
            print(f"HR Score: {first_pred.get('score', 'N/A')}")
            
            # Check critical fields in details
            details = first_pred.get('details', {})
            print("\n📊 Critical Fields in Details:")
            critical_fields = [
                'ab_since_last_hr', 'heating_up_contact_raw_score', 'cold_batter_contact_raw_score',
                'hitter_slg', 'pitcher_slg', 'iso_2024', 'iso_2025_adj_for_trend', 'ev_matchup_score'
            ]
            
            for field in critical_fields:
                value = details.get(field, 'MISSING')
                print(f"  {field}: {value}")
            
            # Check recent data
            recent_data = first_pred.get('recent_N_games_raw_data', {}).get('trends_summary_obj', {})
            print("\n📈 Recent Performance Data:")
            recent_fields = ['avg_avg', 'hr_rate', 'trend_direction']
            for field in recent_fields:
                value = recent_data.get(field, 'MISSING')
                print(f"  {field}: {value}")
                
            return result
        else:
            print("❌ Single Analysis Failed: No predictions returned")
            return None
            
    except Exception as e:
        print(f"❌ Single Analysis Error: {e}")
        return None

def test_bulk_analysis():
    """Test bulk analysis (should fail and fallback to individual calls)"""
    print("\n🔍 Testing Bulk Analysis...")
    
    url = f"{API_BASE}/analyze/bulk-predictions"
    data = {
        "matchups": [
            {"pitcher": "MacKenzie Gore", "team": "SEA"}
        ],
        "sort_by": "score",
        "include_confidence": True
    }
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        
        if result.get('results') and result['results'][0].get('predictions'):
            first_result = result['results'][0]
            first_pred = first_result['predictions'][0]
            print(f"✅ Bulk Analysis Success: {len(first_result['predictions'])} predictions")
            print(f"Player: {first_pred.get('batter_name', 'N/A')}")
            print(f"HR Score: {first_pred.get('score', 'N/A')}")
            
            # Check critical fields in details
            details = first_pred.get('details', {})
            print("\n📊 Critical Fields in Details:")
            critical_fields = [
                'ab_since_last_hr', 'heating_up_contact_raw_score', 'cold_batter_contact_raw_score',
                'hitter_slg', 'pitcher_slg', 'iso_2024', 'iso_2025_adj_for_trend', 'ev_matchup_score'
            ]
            
            for field in critical_fields:
                value = details.get(field, 'MISSING')
                print(f"  {field}: {value}")
            
            # Check recent data
            recent_data = first_pred.get('recent_N_games_raw_data', {}).get('trends_summary_obj', {})
            print("\n📈 Recent Performance Data:")
            recent_fields = ['avg_avg', 'hr_rate', 'trend_direction']
            for field in recent_fields:
                value = recent_data.get(field, 'MISSING')
                print(f"  {field}: {value}")
                
            return result
        else:
            print("❌ Bulk Analysis Failed: No predictions returned")
            print(f"Response: {json.dumps(result, indent=2)[:500]}...")
            return None
            
    except Exception as e:
        print(f"❌ Bulk Analysis Error: {e}")
        return None

def compare_responses(single_result, bulk_result):
    """Compare the two responses to identify differences"""
    print("\n🔬 Comparing Single vs Bulk Responses...")
    
    if not single_result or not bulk_result:
        print("❌ Cannot compare - one or both requests failed")
        return
        
    single_pred = single_result['predictions'][0]
    bulk_pred = bulk_result['results'][0]['predictions'][0]
    
    print(f"\nSingle Player: {single_pred.get('batter_name', 'N/A')}")
    print(f"Bulk Player: {bulk_pred.get('batter_name', 'N/A')}")
    
    # Compare critical fields
    critical_fields = [
        'ab_since_last_hr', 'heating_up_contact_raw_score', 'cold_batter_contact_raw_score',
        'hitter_slg', 'pitcher_slg', 'iso_2024', 'iso_2025_adj_for_trend', 'ev_matchup_score'
    ]
    
    print("\n📊 Field Comparison:")
    for field in critical_fields:
        single_val = single_pred.get('details', {}).get(field, 'MISSING')
        bulk_val = bulk_pred.get('details', {}).get(field, 'MISSING')
        
        if single_val != bulk_val:
            print(f"  ⚠️ {field}: Single={single_val} vs Bulk={bulk_val}")
        else:
            print(f"  ✅ {field}: {single_val}")
    
    # Compare recent data
    single_recent = single_pred.get('recent_N_games_raw_data', {}).get('trends_summary_obj', {})
    bulk_recent = bulk_pred.get('recent_N_games_raw_data', {}).get('trends_summary_obj', {})
    
    print("\n📈 Recent Data Comparison:")
    recent_fields = ['avg_avg', 'hr_rate', 'trend_direction']
    for field in recent_fields:
        single_val = single_recent.get(field, 'MISSING')
        bulk_val = bulk_recent.get(field, 'MISSING')
        
        if single_val != bulk_val:
            print(f"  ⚠️ {field}: Single={single_val} vs Bulk={bulk_val}")
        else:
            print(f"  ✅ {field}: {single_val}")

def main():
    print("🚀 Testing API Response Differences Between Single and Batch Analysis")
    print("="*70)
    
    # Test single analysis
    single_result = test_single_analysis()
    
    # Test bulk analysis
    bulk_result = test_bulk_analysis()
    
    # Compare responses
    compare_responses(single_result, bulk_result)
    
    print("\n" + "="*70)
    print("✅ Test Complete")

if __name__ == "__main__":
    main()