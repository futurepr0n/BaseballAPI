#!/usr/bin/env python3
"""
Debug script to test Kyle Schwarber AB Since HR calculation
"""

import json
import logging
from enhanced_data_handler import EnhancedDataHandler

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    print("🐛 Debugging Kyle Schwarber AB Since HR calculation...")
    
    # Load data (mimic enhanced_main.py initialization)
    try:
        # Load the master data from the enhanced main app
        import requests
        
        # Test via API first to get player ID
        response = requests.post("http://localhost:8000/players/search", json={"name": "Kyle Schwarber"})
        if response.status_code == 200:
            search_results = response.json()
            print(f"🔍 Player search results: {json.dumps(search_results, indent=2)}")
            
            if search_results.get('found') and search_results.get('player'):
                player = search_results['player']
                player_id = player.get('player_id')
                print(f"✅ Found Kyle Schwarber with ID: {player_id}")
                
                # Check the actual API prediction data for details
                print("🔄 Getting prediction data with details...")
                pred_response = requests.post("http://localhost:8000/analyze/pitcher-vs-team", 
                                            json={"pitcher_name": "Logan Allen", "team": "PHI", "max_results": 1})
                
                if pred_response.status_code == 200:
                    pred_data = pred_response.json()
                    schwarber_pred = None
                    for prediction in pred_data.get('predictions', []):
                        if prediction.get('batter_name') == 'Kyle Schwarber':
                            schwarber_pred = prediction
                            break
                    
                    if schwarber_pred:
                        print(f"🏏 Kyle Schwarber prediction data:")
                        print(f"   - AB Since HR: {schwarber_pred.get('ab_since_last_hr')}")
                        print(f"   - H Since HR: {schwarber_pred.get('h_since_last_hr')}")
                        print(f"   - Total AB: {schwarber_pred.get('hitter_total_ab')}")
                        print(f"   - Total HR: {schwarber_pred.get('hitter_total_hr')}")
                        print(f"   - Total H: {schwarber_pred.get('hitter_total_h')}")
                        print(f"   - Total Games: {schwarber_pred.get('hitter_total_games')}")
                        
                        # Get details for debugging
                        details = schwarber_pred.get('details', {})
                        print(f"🔧 Debug details: {json.dumps(details, indent=2)}")
                else:
                    print(f"❌ Prediction API failed: {pred_response.status_code}")
                    print(f"Response: {pred_response.text}")
                
            else:
                print("❌ Kyle Schwarber not found in search results")
        else:
            print(f"❌ API search failed: {response.status_code}")
            print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Debug failed")

if __name__ == "__main__":
    main()