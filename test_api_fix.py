#!/usr/bin/env python3
"""
Test the API fix by running a quick validation
"""

import json
import os

def test_api_roster_fix():
    """Test that the API will now use the cleaned roster"""
    
    print("🧪 TESTING API ROSTER FIX")
    print("="*40)
    
    # Path that the API uses
    api_roster_path = "../BaseballTracker/build/data/rosters.json"
    
    if os.path.exists(api_roster_path):
        print(f"✅ API roster file exists: {api_roster_path}")
        
        with open(api_roster_path, 'r') as f:
            roster_data = json.load(f)
        
        print(f"📊 Roster contains {len(roster_data)} players")
        
        # Test for specific players from the screenshot
        test_players = ["Ceddanne Rafaela", "Alex Bregman", "Brandon Lowe", "Sean Murphy"]
        
        for player_name in test_players:
            found = False
            for player in roster_data:
                if player.get('fullName', '') == player_name:
                    print(f"✅ Found {player_name}:")
                    print(f"   name: '{player.get('name', '')}'")
                    print(f"   fullName: '{player.get('fullName', '')}'")
                    print(f"   team: {player.get('team', '')}")
                    found = True
                    break
            
            if not found:
                print(f"❌ NOT found: {player_name}")
        
        # Check if this is the cleaned roster (should have 1180 players, not 1303)
        if len(roster_data) == 1180:
            print(f"\n🎉 SUCCESS: API is now using CLEANED roster (1180 players)")
        elif len(roster_data) == 1303:
            print(f"\n⚠️  API still using OLD roster (1303 players)")
        else:
            print(f"\n❓ Unexpected roster size: {len(roster_data)} players")
    else:
        print(f"❌ API roster file not found: {api_roster_path}")

def test_name_lookup_chain():
    """Test the complete name lookup chain with real data"""
    
    print(f"\n🔗 TESTING COMPLETE NAME LOOKUP CHAIN")
    print("="*50)
    
    # Test case: Ceddanne Rafaela (should work now)
    test_player = "Ceddanne Rafaela"
    
    # Load the roster that API will use
    api_roster_path = "../BaseballTracker/build/data/rosters.json"
    
    if os.path.exists(api_roster_path):
        with open(api_roster_path, 'r') as f:
            roster_data = json.load(f)
        
        print(f"🎯 Testing lookup chain for: '{test_player}'")
        
        # Step 1: Find player in roster by fullName
        roster_match = None
        for player in roster_data:
            if player.get('fullName', '') == test_player:
                roster_match = player
                break
        
        if roster_match:
            print(f"✅ Step 1 - Found in roster:")
            print(f"   fullName: '{roster_match.get('fullName', '')}'")
            print(f"   name: '{roster_match.get('name', '')}'")
            print(f"   team: {roster_match.get('team', '')}")
            
            # Step 2: Get daily name to search for
            daily_name_to_find = roster_match.get('name', '')
            print(f"\n✅ Step 2 - Daily name to find: '{daily_name_to_find}'")
            
            # Step 3: Check if this name exists in daily data
            daily_file_path = "../BaseballTracker/public/data/2025/june/june_23_2025.json"
            
            if os.path.exists(daily_file_path):
                with open(daily_file_path, 'r') as f:
                    daily_data = json.load(f)
                
                daily_match = None
                for player in daily_data.get('players', []):
                    if player.get('name', '') == daily_name_to_find:
                        daily_match = player
                        break
                
                if daily_match:
                    print(f"✅ Step 3 - Found in daily data:")
                    print(f"   name: '{daily_match.get('name', '')}'")
                    print(f"   team: {daily_match.get('team', '')}")
                    print(f"   AB: {daily_match.get('AB', 'N/A')}")
                    print(f"   H: {daily_match.get('H', 'N/A')}")
                    
                    # Calculate recent avg for verification
                    ab = daily_match.get('AB', 0)
                    h = daily_match.get('H', 0)
                    if ab > 0:
                        avg = h / ab
                        print(f"   Calculated AVG: {avg:.3f}")
                        
                        if avg > 0:
                            print(f"\n🎉 COMPLETE SUCCESS: Name lookup chain works!")
                            print(f"   Recent Avg should show {avg:.3f} instead of 0.000")
                        else:
                            print(f"\n⚠️  Player has 0 hits, so avg will be 0.000 (this is correct)")
                    else:
                        print(f"\n⚠️  Player has 0 AB, so avg will be 0.000 (this is correct)")
                        
                else:
                    print(f"❌ Step 3 - NOT found in daily data")
            else:
                print(f"❌ Step 3 - Daily file not found")
        else:
            print(f"❌ Step 1 - NOT found in roster")

if __name__ == "__main__":
    test_api_roster_fix()
    test_name_lookup_chain()