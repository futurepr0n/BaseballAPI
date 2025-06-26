#!/usr/bin/env python3
"""
Simple debug script to analyze daily JSON player lookup issues.
No external dependencies - just basic Python and JSON.
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
    
    # Load a sample daily JSON file with player data
    daily_path = "../BaseballTracker/public/data/2025/april/april_24_2025.json"
    with open(daily_path, 'r') as f:
        daily_data = json.load(f)
    
    return roster_data, daily_data

def find_roster_match(player_full_name, roster_data):
    """Find matching roster entry for a full name"""
    cleaned_full_name = simple_clean_name(player_full_name)
    
    # Try exact match
    for roster_entry in roster_data:
        if roster_entry.get('fullName_cleaned') == cleaned_full_name:
            return roster_entry
        if roster_entry.get('fullName') == player_full_name:
            return roster_entry
    
    # Try case-insensitive
    for roster_entry in roster_data:
        if roster_entry.get('fullName_cleaned', '').lower() == cleaned_full_name.lower():
            return roster_entry
        if roster_entry.get('fullName', '').lower() == player_full_name.lower():
            return roster_entry
    
    return None

def analyze_daily_lookup(player_full_name, roster_data, daily_players):
    """Analyze the complete lookup chain"""
    print(f"\n=== ANALYZING: '{player_full_name}' ===")
    
    # Step 1: Find in roster
    roster_match = find_roster_match(player_full_name, roster_data)
    if not roster_match:
        print(f"❌ Player '{player_full_name}' not found in roster")
        return None
    
    print(f"✅ Found in roster:")
    print(f"   name: '{roster_match.get('name')}'")
    print(f"   fullName: '{roster_match.get('fullName')}'")
    print(f"   fullName_cleaned: '{roster_match.get('fullName_cleaned')}'")
    print(f"   name_cleaned: '{roster_match.get('name_cleaned')}'")
    
    # Step 2: Look for daily name in daily data
    daily_name_to_find = roster_match.get('name')
    print(f"\n🔍 Looking for daily name: '{daily_name_to_find}'")
    
    matching_daily_players = []
    for daily_player in daily_players:
        if daily_player.get('name') == daily_name_to_find:
            matching_daily_players.append(daily_player)
    
    if matching_daily_players:
        print(f"✅ Found {len(matching_daily_players)} daily entries:")
        for dp in matching_daily_players:
            print(f"   {dp.get('name')} ({dp.get('team')}, {dp.get('playerType')})")
    else:
        print(f"❌ Daily name '{daily_name_to_find}' NOT FOUND in daily data")
        
        # Show similar names for debugging
        similar_names = []
        daily_name_lower = daily_name_to_find.lower()
        for dp in daily_players:
            dp_name = dp.get('name', '')
            if (dp_name.lower().startswith(daily_name_lower[:3]) or 
                daily_name_lower.startswith(dp_name.lower()[:3])):
                similar_names.append(dp_name)
        
        if similar_names:
            print(f"   🔍 Similar names in daily data: {similar_names[:5]}")
    
    return daily_name_to_find if matching_daily_players else None

def main():
    """Main debugging function"""
    roster_data, daily_data = load_test_data()
    daily_players = daily_data.get('players', [])
    
    print(f"📊 Loaded {len(roster_data)} roster entries")
    print(f"📊 Loaded {len(daily_players)} daily players")
    
    # Show data samples
    print(f"\nROSTER SAMPLES:")
    for i in range(min(5, len(roster_data))):
        r = roster_data[i]
        print(f"  '{r.get('name')}' → '{r.get('fullName')}'")
    
    print(f"\nDAILY PLAYERS SAMPLES:")
    for i in range(min(10, len(daily_players))):
        d = daily_players[i]
        print(f"  '{d.get('name')}' ({d.get('team')}, {d.get('playerType')})")
    
    # Test cases from the actual daily data
    test_cases = []
    
    # Get some actual daily players to test reverse lookup
    daily_names_to_test = [dp.get('name') for dp in daily_players[:10] if dp.get('playerType') == 'hitter']
    
    # Convert daily names back to full names to test the process
    print(f"\n" + "="*60)
    print("TESTING DAILY → FULL NAME → DAILY LOOKUP CHAIN")
    print("="*60)
    
    for daily_name in daily_names_to_test[:5]:
        print(f"\n--- Testing with daily name: '{daily_name}' ---")
        
        # Find the roster entry that has this daily name
        roster_entry = None
        for r in roster_data:
            if r.get('name') == daily_name:
                roster_entry = r
                break
        
        if roster_entry:
            full_name = roster_entry.get('fullName')
            print(f"✅ Daily '{daily_name}' maps to full name: '{full_name}'")
            
            # Now test the lookup from full name back to daily
            result = analyze_daily_lookup(full_name, roster_data, daily_players)
            if result == daily_name:
                print(f"✅ ROUND-TRIP SUCCESS: {full_name} → {result}")
            else:
                print(f"❌ ROUND-TRIP FAILED: {full_name} → {result} (expected: {daily_name})")
        else:
            print(f"❌ Daily name '{daily_name}' not found in roster")

if __name__ == "__main__":
    main()