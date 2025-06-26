#!/usr/bin/env python3
"""
Direct API testing using requests to debug name lookup issues.
This script focuses on testing the live API without local imports.
"""

import requests
import json
import time
from typing import Dict, List, Any

class DirectAPITester:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_api_health(self) -> bool:
        """Test API health"""
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Health: {data.get('status')} (Version: {data.get('version')})")
                return True
            else:
                print(f"❌ API Health Check Failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API Health Check Error: {e}")
            return False
    
    def test_data_status(self) -> Dict[str, Any]:
        """Test data initialization status"""
        try:
            response = self.session.get(f"{self.api_url}/data/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                status = data.get('initialization_status')
                print(f"📊 Data Status: {status}")
                
                if status == 'completed':
                    print(f"   Players loaded: {data.get('players_loaded')}")
                    print(f"   Daily game dates: {data.get('daily_game_dates')}")
                    print(f"   Enhanced features: {data.get('enhanced_features')}")
                elif status == 'failed':
                    print(f"   Error: {data.get('error')}")
                
                return data
            else:
                print(f"❌ Data Status Check Failed: {response.status_code}")
                return {}
        except Exception as e:
            print(f"❌ Data Status Check Error: {e}")
            return {}
    
    def test_pitcher_vs_team(self, pitcher_name: str, team: str) -> Dict[str, Any]:
        """Test pitcher vs team analysis"""
        print(f"\n🎯 Testing: {pitcher_name} vs {team}")
        
        payload = {
            "pitcher_name": pitcher_name,
            "team": team,
            "sort_by": "score",
            "min_score": 0,
            "include_confidence": True,
            "max_results": 10
        }
        
        try:
            response = self.session.post(
                f"{self.api_url}/analyze/pitcher-vs-team",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                predictions = data.get('predictions', [])
                
                print(f"   Success: {success}")
                print(f"   Predictions: {len(predictions)}")
                
                if success and predictions:
                    print(f"   📈 Player Analysis:")
                    
                    for i, pred in enumerate(predictions[:5]):
                        player_name = pred.get('player_name', 'Unknown')
                        score = pred.get('score', 0)
                        confidence = pred.get('confidence', 0)
                        
                        # Check for FALLBACK indicators
                        is_fallback = False
                        fallback_indicators = []
                        
                        # Check recent performance
                        recent_perf = pred.get('recent_performance', {})
                        last_7_games = recent_perf.get('last_7_games', [])
                        
                        if len(last_7_games) == 0:
                            is_fallback = True
                            fallback_indicators.append("NO_RECENT_GAMES")
                        
                        # Check confidence level
                        if confidence < 0.5:
                            is_fallback = True
                            fallback_indicators.append("LOW_CONFIDENCE")
                        
                        # Check for fallback in component scores
                        components = pred.get('component_scores', {})
                        if 'fallback_used' in str(components).lower():
                            is_fallback = True
                            fallback_indicators.append("COMPONENT_FALLBACK")
                        
                        # Check analysis notes
                        analysis_notes = pred.get('analysis_notes', [])
                        if any('fallback' in str(note).lower() for note in analysis_notes):
                            is_fallback = True
                            fallback_indicators.append("ANALYSIS_FALLBACK")
                        
                        status_icon = "🔴" if is_fallback else "🟢"
                        status_text = "FALLBACK" if is_fallback else "PRIMARY"
                        
                        print(f"      {i+1}. {status_icon} {player_name}")
                        print(f"         Score: {score:.2f}, Confidence: {confidence:.2f}")
                        print(f"         Status: {status_text}")
                        print(f"         Recent games: {len(last_7_games)}")
                        
                        if is_fallback:
                            print(f"         Fallback reasons: {', '.join(fallback_indicators)}")
                        
                        # Show recent performance details
                        if last_7_games:
                            recent_stats = recent_perf.get('recent_stats', {})
                            avg = recent_stats.get('avg', 0)
                            hr_rate = recent_stats.get('hr_rate', 0)
                            print(f"         Recent: .{int(avg*1000):03d} avg, {hr_rate:.1%} HR rate")
                        else:
                            print(f"         ❌ NO RECENT PERFORMANCE DATA")
                
                return data
            
            else:
                print(f"   ❌ API Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error details: {error_data}")
                except:
                    print(f"   Raw error: {response.text}")
                
                return {'success': False, 'error': f"HTTP {response.status_code}"}
        
        except Exception as e:
            print(f"   ❌ Request Error: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_player_search(self, player_name: str) -> Dict[str, Any]:
        """Test player search functionality"""
        print(f"\n🔍 Searching for player: {player_name}")
        
        payload = {
            "name": player_name,
            "player_type": "hitter"
        }
        
        try:
            response = self.session.post(
                f"{self.api_url}/players/search",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                found = data.get('found', False)
                
                if found:
                    player = data.get('player', {})
                    print(f"   ✅ Found: {player.get('name')} ({player.get('team')})")
                    return data
                else:
                    suggestions = data.get('suggestions', [])
                    print(f"   ❌ Not found directly")
                    if suggestions:
                        print(f"   💡 Suggestions ({len(suggestions)}):")
                        for i, sugg in enumerate(suggestions[:5]):
                            print(f"      {i+1}. {sugg.get('name')} ({sugg.get('team')})")
                    return data
            
            else:
                print(f"   ❌ Search Error: {response.status_code}")
                return {'found': False, 'error': f"HTTP {response.status_code}"}
        
        except Exception as e:
            print(f"   ❌ Search Error: {e}")
            return {'found': False, 'error': str(e)}
    
    def run_focused_debug_tests(self):
        """Run focused tests to identify the name lookup issue"""
        print("🚀 Running Focused Debug Tests for Name Lookup Issues")
        print("=" * 60)
        
        # Test API health
        if not self.test_api_health():
            print("❌ Cannot continue - API not accessible")
            return
        
        # Test data status
        data_status = self.test_data_status()
        if data_status.get('initialization_status') != 'completed':
            print("❌ Cannot continue - Data not initialized")
            return
        
        # Test cases specifically designed to find the issue
        test_cases = [
            {
                "name": "Common Player Test",
                "pitcher": "Blake Snell",
                "team": "SEA",
                "expected": "Should work - common name"
            },
            {
                "name": "Accented Name Test",
                "pitcher": "José Alvarado", 
                "team": "PHI",
                "expected": "Might fail - accented characters"
            },
            {
                "name": "Another Accented Name",
                "pitcher": "Andrés Muñoz",
                "team": "SEA", 
                "expected": "Might fail - accented characters"
            },
            {
                "name": "Common Name Variant",
                "pitcher": "Gerrit Cole",
                "team": "NYY",
                "expected": "Should work - common name"
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            print(f"\n📋 {test_case['name']}")
            print(f"Expected: {test_case['expected']}")
            
            # Test player search first
            self.test_player_search(test_case['pitcher'])
            
            # Test the main analysis
            result = self.test_pitcher_vs_team(test_case['pitcher'], test_case['team'])
            
            # Analyze the result
            success = result.get('success', False)
            predictions = result.get('predictions', [])
            
            # Count primary vs fallback players
            primary_count = 0
            fallback_count = 0
            
            for pred in predictions:
                recent_games = len(pred.get('recent_performance', {}).get('last_7_games', []))
                confidence = pred.get('confidence', 0)
                
                if recent_games > 0 and confidence >= 0.5:
                    primary_count += 1
                else:
                    fallback_count += 1
            
            results.append({
                'test_name': test_case['name'],
                'pitcher': test_case['pitcher'],
                'team': test_case['team'],
                'success': success,
                'total_predictions': len(predictions),
                'primary_count': primary_count,
                'fallback_count': fallback_count,
                'expected': test_case['expected']
            })
        
        # Summary analysis
        print(f"\n📊 Summary Analysis")
        print("=" * 40)
        
        for result in results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test_name']}")
            print(f"   Pitcher: {result['pitcher']} vs {result['team']}")
            print(f"   Total predictions: {result['total_predictions']}")
            print(f"   Primary lookups: {result['primary_count']}")
            print(f"   Fallback lookups: {result['fallback_count']}")
            
            if result['fallback_count'] > result['primary_count']:
                print(f"   ⚠️  More fallbacks than primary lookups!")
            
            if result['primary_count'] == 0 and result['total_predictions'] > 0:
                print(f"   🚨 ALL PREDICTIONS USING FALLBACK - Name lookup failing!")
        
        # Overall pattern analysis
        total_primary = sum(r['primary_count'] for r in results)
        total_fallback = sum(r['fallback_count'] for r in results)
        total_predictions = sum(r['total_predictions'] for r in results)
        
        print(f"\n🎯 Overall Pattern:")
        print(f"   Total predictions: {total_predictions}")
        print(f"   Primary lookups: {total_primary} ({total_primary/total_predictions*100:.1f}%)")
        print(f"   Fallback lookups: {total_fallback} ({total_fallback/total_predictions*100:.1f}%)")
        
        if total_fallback > total_primary:
            print(f"   🚨 ISSUE CONFIRMED: More fallbacks than primary lookups!")
            print(f"   💡 This suggests the comprehensive name lookup chain is failing.")
        else:
            print(f"   ✅ Primary lookups working correctly")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Direct API testing for name lookup issues")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--test-player", help="Test specific player")
    parser.add_argument("--test-team", help="Team for specific test")
    
    args = parser.parse_args()
    
    tester = DirectAPITester(args.api_url)
    
    if args.test_player:
        if args.test_team:
            tester.test_pitcher_vs_team(args.test_player, args.test_team)
        else:
            tester.test_player_search(args.test_player)
    else:
        tester.run_focused_debug_tests()

if __name__ == "__main__":
    main()