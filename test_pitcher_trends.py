#!/usr/bin/env python3
"""
Test script to validate pitcher trend calculation fixes.
This script tests the enhanced pitcher trend logic without requiring full API setup.
"""

import sys
import os
import logging
from collections import defaultdict

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_pitcher_trend_functions():
    """Test the enhanced pitcher trend calculation functions"""
    print("🧪 Testing Enhanced Pitcher Trend Calculation Functions")
    print("=" * 60)
    
    try:
        # Import the enhanced functions
        from pinhead_ported_functions import get_last_n_games_performance_pitcher_ported, calculate_recent_trends_pitcher_ported
        from enhanced_data_handler import EnhancedDataHandler
        
        # Mock data for testing
        mock_roster_data = [
            {
                'fullName': 'Nathan Eovaldi', 
                'fullName_cleaned': 'Nathan Eovaldi',
                'name': 'N. Eovaldi', 
                'team': 'TEX',
                'type': 'pitcher'
            },
            {
                'fullName': 'Gerrit Cole', 
                'fullName_cleaned': 'Gerrit Cole',
                'name': 'G. Cole', 
                'team': 'NYY',
                'type': 'pitcher'
            },
            {
                'fullName': 'Shane Bieber', 
                'fullName_cleaned': 'Shane Bieber',
                'name': 'S. Bieber', 
                'team': 'CLE',
                'type': 'pitcher'
            }
        ]
        
        mock_daily_data = {
            '2025-06-01': {
                'players': [
                    {'name': 'N. Eovaldi', 'playerType': 'pitcher', 'team': 'TEX', 'IP': 6.0, 'H': 5, 'R': 2, 'ER': 2, 'HR': 1, 'BB': 2, 'K': 8, 'ERA': 3.50, 'WHIP': 1.20},
                    {'name': 'G. Cole', 'playerType': 'pitcher', 'team': 'NYY', 'IP': 7.0, 'H': 4, 'R': 1, 'ER': 1, 'HR': 0, 'BB': 1, 'K': 12, 'ERA': 2.25, 'WHIP': 0.85},
                ]
            },
            '2025-06-05': {
                'players': [
                    {'name': 'N. Eovaldi', 'playerType': 'pitcher', 'team': 'TEX', 'IP': 7.0, 'H': 3, 'R': 1, 'ER': 1, 'HR': 0, 'BB': 1, 'K': 10, 'ERA': 2.25, 'WHIP': 0.95},
                    {'name': 'G. Cole', 'playerType': 'pitcher', 'team': 'NYY', 'IP': 6.0, 'H': 7, 'R': 4, 'ER': 4, 'HR': 2, 'BB': 3, 'K': 8, 'ERA': 4.50, 'WHIP': 1.45},
                ]
            },
            '2025-06-10': {
                'players': [
                    {'name': 'N. Eovaldi', 'playerType': 'pitcher', 'team': 'TEX', 'IP': 5.0, 'H': 8, 'R': 4, 'ER': 4, 'HR': 2, 'BB': 3, 'K': 6, 'ERA': 5.40, 'WHIP': 1.60},
                    {'name': 'G. Cole', 'playerType': 'pitcher', 'team': 'NYY', 'IP': 8.0, 'H': 2, 'R': 0, 'ER': 0, 'HR': 0, 'BB': 1, 'K': 14, 'ERA': 1.25, 'WHIP': 0.75},
                ]
            },
            '2025-06-15': {
                'players': [
                    {'name': 'N. Eovaldi', 'playerType': 'pitcher', 'team': 'TEX', 'IP': 6.5, 'H': 4, 'R': 1, 'ER': 1, 'HR': 0, 'BB': 1, 'K': 9, 'ERA': 1.85, 'WHIP': 0.85},
                    {'name': 'G. Cole', 'playerType': 'pitcher', 'team': 'NYY', 'IP': 5.5, 'H': 9, 'R': 5, 'ER': 5, 'HR': 3, 'BB': 2, 'K': 7, 'ERA': 6.75, 'WHIP': 1.85},
                ]
            }
        }
        
        # Test each pitcher
        pitchers_to_test = [
            ('Nathan Eovaldi', 'N. Eovaldi'),
            ('Gerrit Cole', 'G. Cole'),
            ('Shane Bieber', 'S. Bieber')  # This one should fail and use fallback
        ]
        
        trend_results = []
        
        for full_name, expected_daily_name in pitchers_to_test:
            print(f"\n🎯 Testing pitcher: {full_name}")
            print("-" * 40)
            
            try:
                # Test the enhanced pitcher lookup function
                last_games, _ = get_last_n_games_performance_pitcher_ported(
                    full_name, mock_daily_data, mock_roster_data, 7
                )
                
                print(f"📊 Found {len(last_games)} games for {full_name}")
                
                if last_games:
                    # Show the games found
                    for i, game in enumerate(last_games):
                        print(f"  Game {i+1}: Date={game.get('date')}, ERA={game.get('ERA')}, IP={game.get('IP')}")
                    
                    # Calculate trends
                    trends = calculate_recent_trends_pitcher_ported(last_games)
                    trend_direction = trends.get('trend_direction', 'unknown')
                    
                    print(f"📈 Trend Direction: {trend_direction}")
                    print(f"📈 Recent ERA: {trends.get('trend_recent_val', 'N/A')}")
                    print(f"📈 Early ERA: {trends.get('trend_early_val', 'N/A')}")
                    
                    trend_results.append((full_name, trend_direction, len(last_games), 'ported_function'))
                else:
                    print(f"❌ No games found for {full_name} - would use fallback")
                    trend_results.append((full_name, 'stable', 0, 'fallback'))
                    
            except Exception as e:
                print(f"❌ Error testing {full_name}: {e}")
                trend_results.append((full_name, 'error', 0, 'error'))
        
        # Test the fallback functionality
        print(f"\n🔄 Testing Fallback Functionality")
        print("-" * 40)
        
        # Mock master player data for fallback testing
        mock_master_data = {
            '12345': {
                'roster_info': {
                    'fullName': 'Test Pitcher',
                    'name': 'T. Pitcher',
                    'team': 'TST',
                    'type': 'pitcher'
                },
                'pitcher_overall_ev_stats': {
                    'hard_hit_percent': 28.5,  # Good (should trend improving)
                    'brl_percent': 4.2,        # Good
                    'avg_exit_velocity': 86.8  # Good
                }
            },
            '12346': {
                'roster_info': {
                    'fullName': 'Poor Pitcher',
                    'name': 'P. Pitcher',
                    'team': 'TST',
                    'type': 'pitcher'
                },
                'pitcher_overall_ev_stats': {
                    'hard_hit_percent': 42.1,  # Poor (should trend declining)
                    'brl_percent': 9.3,        # Poor
                    'avg_exit_velocity': 91.2  # Poor
                }
            }
        }
        
        # Create a data handler for fallback testing
        data_handler = EnhancedDataHandler(
            master_player_data=mock_master_data,
            league_avg_stats={},
            metric_ranges={},
            roster_data=mock_roster_data,
            daily_game_data=mock_daily_data
        )
        
        # Test fallback calculations
        fallback_results = []
        for pitcher_id, expected_trend in [('12345', 'improving'), ('12346', 'declining')]:
            pitcher_data = mock_master_data[pitcher_id]
            pitcher_name = pitcher_data['roster_info']['fullName']
            
            print(f"🔄 Testing fallback for: {pitcher_name}")
            
            try:
                fallback_result = data_handler._calculate_fallback_pitcher_trend(pitcher_id, pitcher_name)
                trend_direction = fallback_result.get('trend_direction', 'unknown')
                data_source = fallback_result.get('data_source', 'unknown')
                
                print(f"📈 Fallback Trend: {trend_direction} (Source: {data_source})")
                fallback_results.append((pitcher_name, trend_direction, data_source))
                
            except Exception as e:
                print(f"❌ Error in fallback for {pitcher_name}: {e}")
                fallback_results.append((pitcher_name, 'error', 'error'))
        
        # Summary
        print(f"\n📋 SUMMARY")
        print("=" * 60)
        
        print(f"🎯 Primary Function Results:")
        trend_distribution = defaultdict(int)
        for name, trend, games, source in trend_results:
            print(f"  {name}: {trend} ({games} games, {source})")
            trend_distribution[trend] += 1
        
        print(f"\n🔄 Fallback Function Results:")
        for name, trend, source in fallback_results:
            print(f"  {name}: {trend} ({source})")
            trend_distribution[trend] += 1
        
        print(f"\n📊 Overall Trend Distribution:")
        for trend, count in trend_distribution.items():
            print(f"  {trend}: {count}")
        
        # Check if we have varied trends (not all stable)
        non_stable_count = sum(count for trend, count in trend_distribution.items() if trend != 'stable')
        total_count = sum(trend_distribution.values())
        
        if non_stable_count > 0:
            print(f"\n✅ SUCCESS: {non_stable_count}/{total_count} pitchers have non-stable trends!")
            print(f"📈 Trend variation achieved: {non_stable_count/total_count*100:.1f}% non-stable")
        else:
            print(f"\n❌ ISSUE: All pitchers still showing 'stable' trends")
        
        return trend_distribution
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure you're running this from the BaseballAPI directory")
        return None
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🚀 Starting Pitcher Trend Calculation Tests")
    print("This will test the enhanced pitcher trend logic with mock data")
    print()
    
    results = test_pitcher_trend_functions()
    
    if results:
        print(f"\n🎉 Test completed successfully!")
        print(f"📝 Check the output above to verify trend calculations are working")
    else:
        print(f"\n💥 Test failed - check error messages above")