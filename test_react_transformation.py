#!/usr/bin/env python3
"""
Test to simulate what React is doing with the API response
to verify transformation is working correctly
"""

import requests
import json

API_BASE = "http://localhost:8000"

def test_individual_call():
    """Test individual pitcher vs team call"""
    print("🔍 Testing Individual API Call...")
    
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
            
            # Simulate React transformation (simplified version)
            def transform_prediction(prediction):
                outcome_probabilities = prediction.get('outcome_probabilities', {})
                recent_data = prediction.get('recent_N_games_raw_data', {}).get('trends_summary_obj', {})
                details = prediction.get('details', {})
                
                def safe_number(value, default=0):
                    if isinstance(value, (int, float)) and not (isinstance(value, float) and value != value):
                        return value
                    if isinstance(value, str):
                        try:
                            return float(value)
                        except:
                            return default
                    return default
                
                return {
                    'player_name': prediction.get('batter_name') or prediction.get('player_name'),
                    'hr_score': safe_number(prediction.get('score') or prediction.get('hr_score'), 0),
                    'confidence': safe_number(prediction.get('confidence'), 0),
                    
                    # Recent performance
                    'recent_avg': safe_number(recent_data.get('avg_avg') or prediction.get('recent_avg'), 0),
                    'hr_rate': safe_number(recent_data.get('hr_per_pa') or recent_data.get('hr_rate') or prediction.get('hr_rate'), 0),
                    'recent_trend_dir': recent_data.get('trend_direction') or prediction.get('recent_trend_dir') or 'stable',
                    
                    # Due factors - from details
                    'ab_since_last_hr': safe_number(details.get('ab_since_last_hr') or prediction.get('ab_since_last_hr'), 0),
                    'heating_up': safe_number(details.get('heating_up_contact_raw_score') or prediction.get('heating_up'), 0),
                    'cold': abs(safe_number(details.get('cold_batter_contact_raw_score') or prediction.get('cold'), 0)),
                    
                    # Matchup data
                    'hitter_slg': safe_number(details.get('hitter_slg') or prediction.get('hitter_slg'), 0),
                    'pitcher_slg': safe_number(details.get('pitcher_slg') or prediction.get('pitcher_slg'), 0),
                    'iso_2024': safe_number(details.get('iso_2024') or prediction.get('iso_2024'), 0),
                    'iso_2025': safe_number(details.get('iso_2025_adj_for_trend') or details.get('batter_iso_adj') or prediction.get('iso_2025'), 0),
                    'ev_matchup_score': safe_number(details.get('ev_matchup_score') or prediction.get('ev_matchup_score'), 0),
                    
                    # Pitcher stats
                    'pitcher_era': safe_number(prediction.get('pitcher_era'), 4.20),
                    'pitcher_whip': safe_number(prediction.get('pitcher_whip'), 1.30),
                    'pitcher_h_per_game': safe_number(prediction.get('pitcher_h_per_game'), 0),
                    'pitcher_hr_per_game': safe_number(prediction.get('pitcher_hr_per_game'), 0),
                    'pitcher_home_h_total': safe_number(prediction.get('pitcher_home_h_total'), 0),
                    'pitcher_home_games': safe_number(prediction.get('pitcher_home_games'), 0),
                }
            
            transformed = transform_prediction(first_pred)
            
            print(f"✅ Individual Call Success")
            print(f"Player: {transformed['player_name']}")
            print(f"HR Score: {transformed['hr_score']}")
            print(f"\n📊 Transformed Fields:")
            
            critical_fields = [
                'recent_avg', 'hr_rate', 'recent_trend_dir', 'ab_since_last_hr', 
                'heating_up', 'cold', 'hitter_slg', 'pitcher_slg', 'iso_2024', 
                'iso_2025', 'ev_matchup_score', 'pitcher_era', 'pitcher_home_h_total'
            ]
            
            for field in critical_fields:
                value = transformed.get(field, 'MISSING')
                print(f"  {field}: {value}")
                
            return transformed
        else:
            print("❌ Individual Call Failed: No predictions")
            return None
            
    except Exception as e:
        print(f"❌ Individual Call Error: {e}")
        return None

def main():
    print("🚀 Testing React-like API Response Transformation")
    print("="*60)
    
    # Test individual analysis
    individual_result = test_individual_call()
    
    print("\n" + "="*60)
    if individual_result:
        print("✅ Individual transformation working correctly")
        
        # Check for any zero/null values that shouldn't be zero
        issues = []
        if individual_result['recent_avg'] == 0:
            issues.append("recent_avg is 0 - might be missing recent data")
        if individual_result['hitter_slg'] == 0:
            issues.append("hitter_slg is 0 - might be missing hitter data")
        if individual_result['pitcher_home_h_total'] == 0:
            issues.append("pitcher_home_h_total is 0 - might be missing pitcher data")
            
        if issues:
            print("\n⚠️ Potential Data Issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ All critical fields have non-zero values")
    else:
        print("❌ Individual transformation failed")

if __name__ == "__main__":
    main()