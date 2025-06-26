#!/usr/bin/env python3
"""
Live debugging script to trace the exact name lookup failures
"""

import json
import os
import sys

def debug_real_name_lookup():
    """Debug with actual data files to see exactly what's failing"""
    
    print("🔍 LIVE DEBUGGING: Name Lookup Failures")
    print("="*60)
    
    # Check if we can access the actual data files
    base_path = "/Users/futurepr0n/Development/Capping.Pro/Claude-Code"
    
    # Paths to actual data
    roster_path = f"{base_path}/BaseballData/data/rosters.json"
    tracker_data_path = f"{base_path}/BaseballTracker/public/data"
    
    print(f"📁 Checking data paths:")
    print(f"   Roster: {roster_path}")
    print(f"   Tracker Data: {tracker_data_path}")
    
    # Load actual roster data
    if os.path.exists(roster_path):
        print("✅ Found roster file")
        with open(roster_path, 'r') as f:
            roster_data = json.load(f)
        
        print(f"📊 Roster contains {len(roster_data)} players")
        
        # Show sample roster entries
        print("\n📋 Sample Roster Entries:")
        for i, player in enumerate(roster_data[:5]):
            print(f"   {i+1}. name: '{player.get('name', '')}' | fullName: '{player.get('fullName', '')}' | team: {player.get('team', '')}")
    else:
        print("❌ Roster file not found")
        return
    
    # Check for daily data files
    daily_sample_path = f"{tracker_data_path}/2025/june/june_23_2025.json"
    
    if os.path.exists(daily_sample_path):
        print(f"\n✅ Found daily file: {daily_sample_path}")
        with open(daily_sample_path, 'r') as f:
            daily_data = json.load(f)
        
        if 'players' in daily_data:
            players = daily_data['players']
            print(f"📊 Daily file contains {len(players)} player entries")
            
            # Show sample daily entries
            print("\n📋 Sample Daily Player Names:")
            for i, player in enumerate(players[:10]):
                print(f"   {i+1}. name: '{player.get('name', '')}' | team: {player.get('team', '')} | type: {player.get('playerType', '')}")
        else:
            print("⚠️  No 'players' key in daily data")
    else:
        print(f"❌ Daily file not found: {daily_sample_path}")
    
    # Test specific problematic cases from the screenshot
    test_players = [
        "Ceddanne Rafaela",  # BOS
        "Alex Bregman",      # BOS (should be HOU?)
        "Wilson Contreras",  # STL
        "Brandon Lowe",      # TB
        "Sean Murphy"        # ATL
    ]
    
    print(f"\n🎯 Testing Specific Players from Screenshot:")
    print("-" * 50)
    
    for player_name in test_players:
        print(f"\n🔍 Testing: '{player_name}'")
        
        # Find in roster
        roster_match = None
        for player in roster_data:
            if (player.get('fullName', '').lower() == player_name.lower() or
                player.get('name', '').lower() == player_name.lower()):
                roster_match = player
                break
        
        if roster_match:
            print(f"   ✅ Found in roster:")
            print(f"      name: '{roster_match.get('name', '')}'")
            print(f"      fullName: '{roster_match.get('fullName', '')}'")
            print(f"      team: {roster_match.get('team', '')}")
            
            # Try to find in daily data
            daily_name_to_find = roster_match.get('name', '')
            daily_match = None
            
            if os.path.exists(daily_sample_path):
                for daily_player in players:
                    if daily_player.get('name', '') == daily_name_to_find:
                        daily_match = daily_player
                        break
                
                if daily_match:
                    print(f"   ✅ Found in daily data:")
                    print(f"      name: '{daily_match.get('name', '')}'")
                    print(f"      team: {daily_match.get('team', '')}")
                    print(f"      AB: {daily_match.get('AB', 'N/A')}")
                    print(f"      H: {daily_match.get('H', 'N/A')}")
                else:
                    print(f"   ❌ NOT found in daily data (looking for: '{daily_name_to_find}')")
        else:
            print(f"   ❌ NOT found in roster")
    
    # Check the actual data structure that BaseballAPI is receiving
    print(f"\n🔧 API Data Structure Analysis:")
    print("-" * 40)
    
    # The API might be getting data from a different location
    api_data_path = f"{base_path}/BaseballAPI"
    if os.path.exists(api_data_path):
        print(f"✅ BaseballAPI directory exists")
        
        # Check if API has its own data files or if it's reading from BaseballTracker
        potential_paths = [
            f"{api_data_path}/data",
            f"{api_data_path}/../BaseballTracker/public/data",
            f"{api_data_path}/../BaseballTracker/build/data"
        ]
        
        for path in potential_paths:
            if os.path.exists(path):
                print(f"   📁 Found data path: {path}")
            else:
                print(f"   ❌ Missing: {path}")

def identify_data_source_mismatch():
    """Check if API is reading from different data source than expected"""
    
    print(f"\n🎯 IDENTIFYING DATA SOURCE MISMATCH")
    print("="*50)
    
    # The issue might be that BaseballAPI is reading roster from a different location
    potential_roster_locations = [
        "/Users/futurepr0n/Development/Capping.Pro/Claude-Code/BaseballData/data/rosters.json",
        "/Users/futurepr0n/Development/Capping.Pro/Claude-Code/BaseballTracker/public/data/rosters.json", 
        "/Users/futurepr0n/Development/Capping.Pro/Claude-Code/BaseballAPI/data/rosters.json",
        "/Users/futurepr0n/Development/Capping.Pro/Claude-Code/BaseballTracker/build/data/rosters.json"
    ]
    
    print("📋 Checking all potential roster locations:")
    
    for path in potential_roster_locations:
        if os.path.exists(path):
            print(f"   ✅ EXISTS: {path}")
            
            # Quick check of file size and sample content
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    print(f"      📊 Contains {len(data)} players")
                    if data:
                        sample = data[0]
                        print(f"      📝 Sample: name='{sample.get('name', '')}', fullName='{sample.get('fullName', '')}'")
            except Exception as e:
                print(f"      ❌ Error reading: {e}")
        else:
            print(f"   ❌ MISSING: {path}")
    
    print(f"\n💡 LIKELY ISSUE:")
    print("The BaseballAPI might be:")
    print("1. Reading roster from a different location than expected")
    print("2. Not finding the daily data files in the expected path structure")
    print("3. Getting roster data that doesn't have the cleaned fullName fields")
    print("4. The data_loader.py initialization might be failing silently")

if __name__ == "__main__":
    debug_real_name_lookup()
    identify_data_source_mismatch()