#!/usr/bin/env python3
"""
Test script to check if specific player names from PinheadsPlayhouse 
can be found in the daily JSON lookup system.
"""

import os
import json
import re

def simple_clean_name(name_input):
    """Simple name cleaner without pandas"""
    if not name_input:
        return None
    
    name = str(name_input)
    
    # Handle "LastName, FirstName" format
    if ',' in name: 
        parts = name.split(',', 1)
        if len(parts) == 2:
            name = f"{parts[1].strip()} {parts[0].strip()}"
    
    # Standardize whitespace and title case
    name = re.sub(r'\s+', ' ', name).strip().title()
    
    # Remove periods from initials
    name = re.sub(r'(?<=\b[A-Z])\.(?=\s|$)', '', name)
    
    return name

def load_test_data():
    """Load sample data for testing"""
    # Load roster data
    roster_path = "../BaseballTracker/build/data/rosters.json"
    with open(roster_path, 'r') as f:
        roster_data = json.load(f)
    
    # Clean roster names
    for entry in roster_data:
        entry['fullName_cleaned'] = simple_clean_name(entry.get('fullName'))
        entry['name_cleaned'] = simple_clean_name(entry.get('name'))
    
    # Load multiple daily JSON files to have more player data
    daily_files = [
        "../BaseballTracker/public/data/2025/april/april_24_2025.json",
        "../BaseballTracker/public/data/2025/april/april_30_2025.json",
        "../BaseballTracker/public/data/2025/april/april_11_2025.json"
    ]
    
    all_daily_players = []
    for daily_path in daily_files:
        try:
            with open(daily_path, 'r') as f:
                daily_data = json.load(f)
                players = daily_data.get('players', [])
                all_daily_players.extend(players)
                print(f"Loaded {len(players)} players from {os.path.basename(daily_path)}")
        except Exception as e:
            print(f"Could not load {daily_path}: {e}")
    
    return roster_data, all_daily_players

def test_get_last_n_games_performance_logic(player_full_name_resolved, roster_data, daily_players):
    """
    Replicate the exact logic from get_last_n_games_performance() function
    """
    print(f"\n=== TESTING: '{player_full_name_resolved}' ===")
    
    daily_player_json_name = None
    
    # Strategy 1: Direct roster lookup (fullName → name) - multiple field checks
    print("\n--- Strategy 1: Direct roster lookup ---")
    for p_info_roster in roster_data:
        full_names_to_check = [
            p_info_roster.get('fullName_cleaned'),
            p_info_roster.get('fullName'), 
            p_info_roster.get('fullName_resolved')  # This will be None for most entries
        ]
        
        for full_name_check in full_names_to_check:
            if full_name_check == player_full_name_resolved:
                daily_player_json_name = p_info_roster.get('name')
                print(f"✅ FOUND: '{full_name_check}' → '{daily_player_json_name}'")
                break
        
        if daily_player_json_name:
            break
    
    if not daily_player_json_name:
        print("❌ No match in Strategy 1")
        
        # Debug: show what we're comparing against
        print(f"   Looking for exact match of: '{player_full_name_resolved}'")
        close_matches = []
        for p in roster_data[:20]:  # Check first 20 for debugging
            fn_cleaned = p.get('fullName_cleaned')
            fn_original = p.get('fullName')
            if fn_cleaned and (player_full_name_resolved.lower() in fn_cleaned.lower() or 
                              fn_cleaned.lower() in player_full_name_resolved.lower()):
                close_matches.append(f"'{fn_original}' (cleaned: '{fn_cleaned}')")
        
        if close_matches:
            print(f"   Close matches found: {close_matches[:3]}")
    
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
                    print(f"✅ FOUND: '{full_name_check}' → '{daily_player_json_name}'")
                    break
            
            if daily_player_json_name:
                break
        
        if not daily_player_json_name:
            print("❌ No match in Strategy 2")
    
    # If we found a daily name, check if it exists in actual daily data
    if daily_player_json_name:
        print(f"\n🔍 Checking if '{daily_player_json_name}' exists in daily data...")
        daily_matches = [p for p in daily_players if p.get('name') == daily_player_json_name]
        if daily_matches:
            print(f"✅ Found {len(daily_matches)} instances in daily data:")
            for dm in daily_matches[:3]:
                print(f"   {dm.get('name')} ({dm.get('team')}, {dm.get('playerType')})")
        else:
            print(f"❌ '{daily_player_json_name}' NOT FOUND in daily data!")
            # Show similar daily names
            similar = [p.get('name') for p in daily_players 
                      if p.get('name', '').lower().startswith(daily_player_json_name[:3].lower())][:5]
            if similar:
                print(f"   Similar daily names: {similar}")
    
    return daily_player_json_name

def main():
    """Test with common baseball player names that might come from PinheadsPlayhouse"""
    roster_data, daily_players = load_test_data()
    
    print(f"\n📊 Total roster entries: {len(roster_data)}")
    print(f"📊 Total daily players: {len(daily_players)}")
    
    # Test cases - common MLB player names that might be requested
    test_cases = [
        # These should work (using exact roster fullName values)
        "Jonathan India",
        "Bobby Witt Jr.", 
        "Vinnie Pasquantino",
        "Salvador Perez",
        
        # These might be problematic (different formatting)
        "Aaron Judge",
        "Mookie Betts", 
        "Vladimir Guerrero Jr.",
        "Fernando Tatis Jr.",
        
        # Edge cases
        "Sal Perez",  # nickname vs full name
        "Bobby Witt",  # missing Jr.
        "Vlad Guerrero Jr.",  # nickname
    ]
    
    print("\n" + "="*80)
    print("TESTING PLAYER NAME LOOKUPS")
    print("="*80)
    
    successful_lookups = 0
    failed_lookups = []
    
    for test_name in test_cases:
        result = test_get_last_n_games_performance_logic(test_name, roster_data, daily_players)
        if result:
            successful_lookups += 1
            print(f"🎯 SUCCESS: '{test_name}' → '{result}'")
        else:
            failed_lookups.append(test_name)
            print(f"💥 FAILED: '{test_name}' → None")
        print("\n" + "-"*50)
    
    print(f"\n📈 SUMMARY:")
    print(f"✅ Successful lookups: {successful_lookups}/{len(test_cases)}")
    print(f"❌ Failed lookups: {len(failed_lookups)}")
    if failed_lookups:
        print(f"   Failed names: {failed_lookups}")

if __name__ == "__main__":
    main()