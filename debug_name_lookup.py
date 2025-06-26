#!/usr/bin/env python3
"""
Debug script for name lookup issues in BaseballAPI.
Tests the comprehensive name lookup chain and identifies where it breaks.
"""

import requests
import json
import time
from typing import Dict, List, Any, Optional
import sys
import os

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_loader import get_last_n_games_performance, initialize_data
from utils import clean_player_name, match_player_name_to_roster

class NameLookupDebugger:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.test_results = []
        
        # Initialize data locally to test the lookup chain
        print("🔄 Initializing local data for debugging...")
        try:
            result = initialize_data()
            if result and len(result) >= 5:
                (self.master_player_data, self.player_id_to_name_map, 
                 self.name_to_player_id_map, self.daily_game_data, 
                 self.roster_data) = result[:5]
                print("✅ Local data initialized successfully")
            else:
                print("❌ Failed to initialize local data")
                self.master_player_data = None
        except Exception as e:
            print(f"❌ Error initializing data: {e}")
            self.master_player_data = None
    
    def test_api_health(self) -> bool:
        """Test if the API is running and responsive"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API is running and responsive")
                return True
            else:
                print(f"❌ API returned status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Failed to connect to API: {e}")
            return False
    
    def test_data_status(self) -> Dict[str, Any]:
        """Test API data initialization status"""
        try:
            response = requests.get(f"{self.api_base_url}/data/status", timeout=10)
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ API Data Status: {status_data.get('initialization_status')}")
                if status_data.get('initialization_status') == 'completed':
                    print(f"   Players loaded: {status_data.get('players_loaded', 'N/A')}")
                    print(f"   Daily game dates: {status_data.get('daily_game_dates', 'N/A')}")
                return status_data
            else:
                print(f"❌ Failed to get data status: {response.status_code}")
                return {}
        except Exception as e:
            print(f"❌ Error getting data status: {e}")
            return {}
    
    def test_pitcher_vs_team_api(self, pitcher_name: str, team: str) -> Dict[str, Any]:
        """Test the main pitcher vs team API endpoint"""
        try:
            payload = {
                "pitcher_name": pitcher_name,
                "team": team,
                "sort_by": "score",
                "min_score": 0,
                "include_confidence": True,
                "max_results": 5
            }
            
            print(f"\n🔍 Testing API call: {pitcher_name} vs {team}")
            response = requests.post(
                f"{self.api_base_url}/analyze/pitcher-vs-team",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                success = result.get('success', False)
                predictions = result.get('predictions', [])
                
                print(f"   ✅ API Response Success: {success}")
                print(f"   📊 Predictions returned: {len(predictions)}")
                
                # Analyze prediction details
                if predictions:
                    for i, pred in enumerate(predictions[:3]):  # Show first 3
                        player_name = pred.get('player_name', 'Unknown')
                        score = pred.get('score', 0)
                        confidence = pred.get('confidence', 0)
                        recent_stats = pred.get('recent_performance', {})
                        
                        print(f"      {i+1}. {player_name}: Score={score:.2f}, Confidence={confidence:.2f}")
                        
                        # Check for FALLBACK indicators
                        if 'FALLBACK' in str(pred) or confidence < 0.5:
                            print(f"         🚨 FALLBACK detected for {player_name}")
                        
                        # Check recent stats
                        games_found = len(recent_stats.get('last_7_games', []))
                        print(f"         📈 Recent games: {games_found}")
                        
                        if games_found == 0:
                            print(f"         ❌ No recent games found - this indicates lookup failure")
                
                return result
            
            else:
                print(f"   ❌ API call failed: {response.status_code}")
                try:
                    error_details = response.json()
                    print(f"   Error details: {error_details}")
                except:
                    print(f"   Raw error: {response.text}")
                return {'error': f"HTTP {response.status_code}", 'success': False}
        
        except Exception as e:
            print(f"   ❌ Exception during API call: {e}")
            return {'error': str(e), 'success': False}
    
    def test_local_name_lookup(self, player_full_name: str) -> Dict[str, Any]:
        """Test the local name lookup chain directly"""
        if not self.master_player_data:
            return {'error': 'Local data not available', 'success': False}
        
        print(f"\n🔍 Testing local name lookup for: '{player_full_name}'")
        
        try:
            # Test the comprehensive lookup chain
            roster_data_list = self.roster_data if hasattr(self, 'roster_data') else []
            daily_data = self.daily_game_data if hasattr(self, 'daily_game_data') else {}
            
            print(f"   📋 Available roster entries: {len(roster_data_list)}")
            print(f"   📅 Available daily data dates: {len(daily_data)}")
            
            # Call the actual function that's failing
            last_games, at_bats = get_last_n_games_performance(
                player_full_name, 7, roster_data_list, daily_data
            )
            
            result = {
                'player_name': player_full_name,
                'games_found': len(last_games),
                'at_bats_found': len(at_bats),
                'success': len(last_games) > 0
            }
            
            if len(last_games) > 0:
                print(f"   ✅ Found {len(last_games)} games")
                # Show recent performance
                for i, game in enumerate(last_games[:3]):
                    print(f"      Game {i+1}: {game.get('date')} - {game.get('H')}/{game.get('AB')} (.{int(game.get('AVG', 0)*1000):03d})")
            else:
                print(f"   ❌ No games found - this should trigger FALLBACK")
            
            return result
            
        except Exception as e:
            print(f"   ❌ Error in local lookup: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e), 'success': False}
    
    def test_roster_name_matching(self, player_full_name: str) -> Dict[str, Any]:
        """Test roster name matching specifically"""
        if not hasattr(self, 'roster_data'):
            return {'error': 'Roster data not available', 'success': False}
        
        print(f"\n🔍 Testing roster matching for: '{player_full_name}'")
        
        roster_matches = []
        player_clean = clean_player_name(player_full_name)
        
        for roster_entry in self.roster_data:
            fullname = roster_entry.get('fullName', '')
            fullname_cleaned = roster_entry.get('fullName_cleaned', '')
            fullname_resolved = roster_entry.get('fullName_resolved', '')
            name = roster_entry.get('name', '')
            
            # Test different matching strategies
            if any(name_variant.lower() == player_full_name.lower() for name_variant in [fullname, fullname_cleaned, fullname_resolved] if name_variant):
                roster_matches.append({
                    'roster_entry': roster_entry,
                    'match_type': 'exact',
                    'matched_field': 'fullName variants'
                })
        
        print(f"   📋 Exact roster matches found: {len(roster_matches)}")
        
        for match in roster_matches:
            entry = match['roster_entry']
            print(f"      - {entry.get('fullName')} ({entry.get('team')}) -> name: '{entry.get('name')}'")
        
        return {
            'player_name': player_full_name,
            'roster_matches': len(roster_matches),
            'matches': roster_matches[:5],  # Limit output
            'success': len(roster_matches) > 0
        }
    
    def run_comprehensive_tests(self):
        """Run comprehensive tests to identify the name lookup issue"""
        print("🚀 Starting Comprehensive Name Lookup Debug Tests")
        print("=" * 60)
        
        # Test API health
        if not self.test_api_health():
            print("❌ Cannot continue - API is not accessible")
            return
        
        # Test data status
        self.test_data_status()
        
        # Test cases - mix of players that should work vs fail
        test_cases = [
            # These should work (common players)
            {"pitcher": "Blake Snell", "team": "SEA", "expected": "success"},
            {"pitcher": "Gerrit Cole", "team": "NYY", "expected": "success"},
            {"pitcher": "Spencer Strider", "team": "ATL", "expected": "success"},
            
            # These might fail (less common or name variations)
            {"pitcher": "José Alvarado", "team": "PHI", "expected": "might_fail"},
            {"pitcher": "Cristian Javier", "team": "HOU", "expected": "might_fail"},
            {"pitcher": "Andrés Muñoz", "team": "SEA", "expected": "might_fail"},
        ]
        
        print("\n📊 Running Test Cases")
        print("-" * 40)
        
        for test_case in test_cases:
            pitcher = test_case["pitcher"]
            team = test_case["team"]
            expected = test_case["expected"]
            
            print(f"\n🎯 Test Case: {pitcher} vs {team} (Expected: {expected})")
            
            # Test API call
            api_result = self.test_pitcher_vs_team_api(pitcher, team)
            
            # Test local lookup for team batters
            if hasattr(self, 'roster_data'):
                team_batters = [entry for entry in self.roster_data if entry.get('team') == team and entry.get('type') == 'hitter']
                print(f"   👥 Team {team} batters available: {len(team_batters)}")
                
                # Test a few batter lookups
                for batter in team_batters[:3]:
                    batter_name = batter.get('fullName', '')
                    if batter_name:
                        local_result = self.test_local_name_lookup(batter_name)
                        roster_result = self.test_roster_name_matching(batter_name)
                        
                        if not local_result.get('success', False):
                            print(f"      ❌ LOOKUP FAILURE: {batter_name}")
                            print(f"         Roster match: {roster_result.get('success', False)}")
                        else:
                            print(f"      ✅ LOOKUP SUCCESS: {batter_name} ({local_result.get('games_found', 0)} games)")
            
            # Store results
            self.test_results.append({
                'pitcher': pitcher,
                'team': team,
                'expected': expected,
                'api_success': api_result.get('success', False),
                'api_predictions': len(api_result.get('predictions', [])),
                'timestamp': time.time()
            })
        
        print("\n📋 Summary of Results")
        print("-" * 40)
        
        for result in self.test_results:
            status = "✅" if result['api_success'] else "❌"
            print(f"{status} {result['pitcher']} vs {result['team']}: {result['api_predictions']} predictions")
        
        # Analyze patterns
        successful_tests = [r for r in self.test_results if r['api_success']]
        failed_tests = [r for r in self.test_results if not r['api_success']]
        
        print(f"\n📊 Pattern Analysis:")
        print(f"   Successful tests: {len(successful_tests)}/{len(self.test_results)}")
        print(f"   Failed tests: {len(failed_tests)}/{len(self.test_results)}")
        
        if failed_tests:
            print(f"\n❌ Failed Test Cases:")
            for failed in failed_tests:
                print(f"   - {failed['pitcher']} vs {failed['team']}")
    
    def test_specific_player_lookup(self, player_name: str):
        """Test specific player lookup in detail"""
        print(f"\n🔍 Detailed Player Lookup Test: '{player_name}'")
        print("-" * 50)
        
        # Test roster matching
        roster_result = self.test_roster_name_matching(player_name)
        
        # Test local lookup
        local_result = self.test_local_name_lookup(player_name)
        
        # Test variations
        variations = [
            player_name,
            clean_player_name(player_name),
            player_name.replace(" Jr.", "").replace(" Sr.", "").strip(),
            player_name.replace("José", "Jose").replace("Andrés", "Andres")
        ]
        
        print(f"\n🔄 Testing name variations:")
        for variation in set(variations):
            if variation != player_name:
                print(f"   Testing: '{variation}'")
                var_result = self.test_local_name_lookup(variation)
                if var_result.get('success'):
                    print(f"      ✅ SUCCESS with variation!")

def main():
    """Main function to run the debug tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug BaseballAPI name lookup issues")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--player", help="Test specific player name")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    
    args = parser.parse_args()
    
    debugger = NameLookupDebugger(args.api_url)
    
    if args.player:
        # Test specific player
        debugger.test_specific_player_lookup(args.player)
    elif args.quick:
        # Quick tests
        print("🚀 Running Quick Tests")
        debugger.test_api_health()
        debugger.test_data_status()
        debugger.test_pitcher_vs_team_api("Blake Snell", "SEA")
    else:
        # Full comprehensive tests
        debugger.run_comprehensive_tests()

if __name__ == "__main__":
    main()