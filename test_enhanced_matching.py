#!/usr/bin/env python3
"""
Test script for enhanced name matching functions
"""

import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import match_player_name_to_roster, clean_player_name

def test_enhanced_name_matching():
    """Test the enhanced name matching with realistic data"""
    
    print("🧪 TESTING ENHANCED NAME MATCHING FUNCTIONS")
    print("="*60)
    
    # Mock roster data simulating our cleaned roster structure
    mock_roster = [
        {
            'name': 'A. Garcia',
            'name_cleaned': 'A Garcia',  # After clean_player_name()
            'fullName': 'Aramis Garcia',
            'fullName_cleaned': 'Aramis Garcia',
            'team': 'ARI',
            'type': 'hitter'
        },
        {
            'name': 'A. Martinez', 
            'name_cleaned': 'A Martinez',
            'fullName': 'Angel Martinez',
            'fullName_cleaned': 'Angel Martinez',
            'team': 'CLE',
            'type': 'hitter'
        },
        {
            'name': 'J. Rodriguez',
            'name_cleaned': 'J Rodriguez', 
            'fullName': 'Jose Rodriguez',
            'fullName_cleaned': 'Jose Rodriguez',
            'team': 'SEA',
            'type': 'hitter'
        },
        {
            'name': 'C. Kimbrel',
            'name_cleaned': 'C Kimbrel',
            'fullName': 'Craig Kimbrel', 
            'fullName_cleaned': 'Craig Kimbrel',
            'team': 'ATL',
            'type': 'pitcher'
        }
    ]
    
    # Test cases simulating daily JSON name → roster matching
    test_cases = [
        {
            'daily_name': 'A. Garcia',
            'expected_full_name': 'Aramis Garcia',
            'description': 'Exact match with period'
        },
        {
            'daily_name': 'A Garcia',  # Period removed by clean_player_name
            'expected_full_name': 'Aramis Garcia', 
            'description': 'Match without period'
        },
        {
            'daily_name': 'a. garcia',  # Different case
            'expected_full_name': 'Aramis Garcia',
            'description': 'Case insensitive match'
        },
        {
            'daily_name': 'A.Garcia',  # No space
            'expected_full_name': 'Aramis Garcia',
            'description': 'No space after period'
        },
        {
            'daily_name': 'Angel Martinez',  # Full name in daily (shouldn't happen but test anyway)
            'expected_full_name': 'Angel Martinez',
            'description': 'Full name direct match'
        }
    ]
    
    print("📊 TESTING MATCH_PLAYER_NAME_TO_ROSTER:")
    print("-" * 40)
    
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        daily_name = test_case['daily_name']
        expected = test_case['expected_full_name']
        description = test_case['description']
        
        print(f"\n{i}. {description}")
        print(f"   Input: '{daily_name}'")
        print(f"   Expected: '{expected}'")
        
        # Test the enhanced function
        result = match_player_name_to_roster(daily_name, mock_roster)
        
        print(f"   Result: '{result}'")
        
        if result == expected:
            print(f"   ✅ SUCCESS")
            success_count += 1
        else:
            print(f"   ❌ FAILED")
    
    print(f"\n📈 MATCH RESULTS: {success_count}/{len(test_cases)} tests passed")
    
    # Test clean_player_name function
    print("\n🧹 TESTING CLEAN_PLAYER_NAME:")
    print("-" * 30)
    
    clean_test_cases = [
        ('A. Garcia', 'A Garcia'),  # Should remove period
        ('Garcia, Aramis', 'Aramis Garcia'),  # Should handle CSV format
        ('J.  Rodriguez', 'J Rodriguez'),  # Should handle extra spaces
        ('Martinez Jr.', 'Martinez Jr'),  # Should handle suffixes
    ]
    
    clean_success = 0
    for input_name, expected_clean in clean_test_cases:
        result = clean_player_name(input_name)
        print(f"'{input_name}' → '{result}' (expected: '{expected_clean}')")
        
        if result == expected_clean:
            print("   ✅ SUCCESS")
            clean_success += 1
        else:
            print("   ❌ FAILED")
    
    print(f"\n📈 CLEAN RESULTS: {clean_success}/{len(clean_test_cases)} tests passed")
    
    # Overall results
    total_tests = len(test_cases) + len(clean_test_cases)
    total_success = success_count + clean_success
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {total_success}")
    print(f"   Success Rate: {(total_success/total_tests)*100:.1f}%")
    
    if total_success == total_tests:
        print("\n🎉 ALL TESTS PASSED! Enhanced name matching is working correctly.")
    else:
        print(f"\n⚠️  {total_tests - total_success} tests failed. Review function logic.")
    
    return total_success == total_tests

def simulate_daily_lookup_process():
    """Simulate the complete daily lookup process"""
    
    print("\n" + "="*60)
    print("🔄 SIMULATING COMPLETE DAILY LOOKUP PROCESS")
    print("="*60)
    
    # Simulate the exact process from get_last_n_games_performance
    player_full_name_resolved = "Aramis Garcia"  # From PinheadsPlayhouse
    
    # Mock roster (same as above)
    roster_data_list = [
        {
            'name': 'A. Garcia',
            'fullName_cleaned': 'Aramis Garcia',
            'team': 'ARI'
        }
    ]
    
    # Mock daily data
    mock_daily_data = {
        '2025-06-23': {
            'players': [
                {
                    'name': 'A. Garcia',
                    'team': 'ARI',
                    'playerType': 'hitter',
                    'AB': 4,
                    'H': 2,
                    'HR': 1
                }
            ]
        }
    }
    
    print(f"🎯 Looking for player: '{player_full_name_resolved}'")
    
    # Strategy 1: Direct roster lookup
    daily_player_json_name = None
    for p_info_roster in roster_data_list:
        if p_info_roster.get('fullName_cleaned') == player_full_name_resolved:
            daily_player_json_name = p_info_roster.get('name')
            print(f"✅ Strategy 1 SUCCESS: Found daily name '{daily_player_json_name}'")
            break
    
    if daily_player_json_name:
        # Now simulate finding this player in daily data
        for date, day_data in mock_daily_data.items():
            for player in day_data.get('players', []):
                if player.get('name') == daily_player_json_name:
                    print(f"✅ Daily data lookup SUCCESS: Found '{daily_player_json_name}' in {date}")
                    print(f"   Player stats: AB={player['AB']}, H={player['H']}, HR={player['HR']}")
                    return True
    
    print("❌ Complete lookup process FAILED")
    return False

if __name__ == "__main__":
    # Run the tests
    matching_success = test_enhanced_name_matching()
    lookup_success = simulate_daily_lookup_process()
    
    print(f"\n🏆 FINAL SUMMARY:")
    print(f"   Enhanced Matching: {'✅ PASS' if matching_success else '❌ FAIL'}")
    print(f"   Complete Lookup: {'✅ PASS' if lookup_success else '❌ FAIL'}")
    
    if matching_success and lookup_success:
        print(f"\n🎉 ALL SYSTEMS GO! The enhanced name matching should fix the 0 statistics issue.")
    else:
        print(f"\n⚠️  Some tests failed. Review the implementation before deployment.")