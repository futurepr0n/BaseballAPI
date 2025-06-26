#!/usr/bin/env python3
"""
Debug script to analyze why daily JSON player lookups are failing.
Tests the exact flow from fullName → daily JSON player name matching.
"""

import os
import json
import sys
sys.path.append(os.path.dirname(__file__))

from utils import clean_player_name, match_player_name_to_roster

def load_test_data():
    """Load sample data for testing"""
    # Load roster data
    roster_path = "../BaseballTracker/build/data/rosters.json"
    with open(roster_path, 'r') as f:
        roster_data = json.load(f)
    
    # Clean roster names
    for entry in roster_data:
        entry['fullName_cleaned'] = clean_player_name(entry.get('fullName'))
        entry['name_cleaned'] = clean_player_name(entry.get('name'))
    
    # Load a sample daily JSON file with player data
    daily_path = "../BaseballTracker/public/data/2025/april/april_24_2025.json"
    with open(daily_path, 'r') as f:
        daily_data = json.load(f)
    
    return roster_data, daily_data

def test_name_matching_strategies(player_full_name_resolved, roster_data, sample_daily_players):
    """Test the 4-strategy lookup system from get_last_n_games_performance"""
    print(f"\n=== TESTING NAME MATCHING FOR: '{player_full_name_resolved}' ===")
    
    daily_player_json_name = None
    
    print("\n--- Strategy 1: Direct roster lookup (fullName → name) ---")
    for p_info_roster in roster_data:
        full_names_to_check = [
            p_info_roster.get('fullName_cleaned'),
            p_info_roster.get('fullName'), 
            p_info_roster.get('fullName_resolved')
        ]
        
        for full_name_check in full_names_to_check:
            if full_name_check == player_full_name_resolved:
                daily_player_json_name = p_info_roster.get('name')
                print(f"✅ MATCH FOUND: {full_name_check} → {daily_player_json_name}")
                break
        
        if daily_player_json_name:
            break
    
    if not daily_player_json_name:
        print("❌ No match in Strategy 1")
    
    # Strategy 2: Enhanced case-insensitive matching
    if not daily_player_json_name:
        print("\n--- Strategy 2: Case-insensitive matching ---")
        for p_info_roster in roster_data:
            full_names_to_check = [
                p_info_roster.get('fullName_cleaned', '').lower(),
                p_info_roster.get('fullName', '').lower(), 
                p_info_roster.get('fullName_resolved', '').lower()
            ]
            
            for full_name_check in full_names_to_check:
                if full_name_check == player_full_name_resolved.lower():
                    daily_player_json_name = p_info_roster.get('name')
                    print(f"✅ MATCH FOUND: {full_name_check} → {daily_player_json_name}")
                    break
            
            if daily_player_json_name:
                break
        
        if not daily_player_json_name:
            print("❌ No match in Strategy 2")
    
    # Strategy 3: Search in daily data with enhanced matching
    if not daily_player_json_name:
        print("\n--- Strategy 3: Daily data reverse lookup ---")
        print(f"Sample daily players: {[p.get('name') for p in sample_daily_players[:5]]}")
        
        for player_daily_stat_rev in sample_daily_players:
            daily_name = player_daily_stat_rev.get('name', '')
            
            # Try multiple matching approaches
            resolved_daily_to_full = match_player_name_to_roster(
                clean_player_name(daily_name), 
                roster_data
            )
            
            # Also try without cleaning to preserve original format
            if not resolved_daily_to_full:
                resolved_daily_to_full = match_player_name_to_roster(
                    daily_name, 
                    roster_data
                )
            
            print(f"  Daily name '{daily_name}' → resolved to '{resolved_daily_to_full}'")
            
            # Check both exact and case-insensitive matches
            if (resolved_daily_to_full == player_full_name_resolved or 
                (resolved_daily_to_full and resolved_daily_to_full.lower() == player_full_name_resolved.lower())):
                daily_player_json_name = daily_name
                print(f"✅ MATCH FOUND: {daily_name} → {resolved_daily_to_full}")
                break
        
        if not daily_player_json_name:
            print("❌ No match in Strategy 3")
    
    # Strategy 4: Direct name pattern matching as last resort
    if not daily_player_json_name:
        print("\n--- Strategy 4: Pattern matching ---")
        for player_daily_stat_rev in sample_daily_players:
            daily_name = player_daily_stat_rev.get('name', '')
            
            # Check if daily name could be an abbreviation of our full name
            if daily_name and len(daily_name.split()) >= 2:
                daily_parts = daily_name.replace('.', '').split()
                full_parts = player_full_name_resolved.split()
                
                if (len(daily_parts) == len(full_parts) and 
                    len(daily_parts[0]) <= 2 and  # First part is initial(s)
                    daily_parts[0].upper() == full_parts[0][0].upper() and  # Initial matches
                    daily_parts[-1].lower() == full_parts[-1].lower()):  # Last name matches
                    daily_player_json_name = daily_name
                    print(f"✅ PATTERN MATCH: {daily_name} ↔ {player_full_name_resolved}")
                    break
        
        if not daily_player_json_name:
            print("❌ No match in Strategy 4")
    
    print(f"\n🎯 FINAL RESULT: '{player_full_name_resolved}' → '{daily_player_json_name}'")
    return daily_player_json_name

def test_specific_players():
    """Test with specific players that are likely to have issues"""
    roster_data, daily_data = load_test_data()
    sample_daily_players = daily_data.get('players', [])
    
    print(f"Loaded {len(roster_data)} roster entries")
    print(f"Loaded {len(sample_daily_players)} daily players")
    
    # Test some common cases
    test_cases = [
        "Aaron Judge",      # Should be A. Judge in daily
        "Mookie Betts",     # Should be M. Betts in daily  
        "Bobby Witt Jr.",   # Should be B. Witt Jr. in daily
        "Vladimir Guerrero Jr.",
        "Sal Perez",       # Should be S. Perez
    ]
    
    print("\n" + "="*80)
    print("ROSTER SAMPLE (name → fullName):")
    for i, p in enumerate(roster_data[:10]):
        print(f"  {p.get('name')} → {p.get('fullName')}")
    
    print(f"\nDAILY PLAYERS SAMPLE:")
    for i, p in enumerate(sample_daily_players[:10]):
        print(f"  {p.get('name')} ({p.get('team')})")
    
    print("\n" + "="*80)
    print("TESTING SPECIFIC CASES:")
    
    for test_name in test_cases:
        result = test_name_matching_strategies(test_name, roster_data, sample_daily_players)
        if result:
            # Now test if this daily name exists in actual daily data
            found_in_daily = any(p.get('name') == result for p in sample_daily_players)
            print(f"📊 Daily data contains '{result}': {found_in_daily}")
        print("\n" + "-"*50)

if __name__ == "__main__":
    test_specific_players()