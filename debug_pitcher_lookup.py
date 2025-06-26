#!/usr/bin/env python3
"""
Debug script specifically for pitcher lookup issues.
"""

import sys
import os

# Ensure we can import from the local directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_pitcher_lookup():
    """Debug why certain pitchers aren't found"""
    
    try:
        from data_loader import initialize_data
        
        print("🔄 Initializing data...")
        
        # Initialize data
        result = initialize_data()
        if not result or len(result) < 5:
            print("❌ Failed to initialize data")
            return
        
        (master_player_data, player_id_to_name_map, name_to_player_id_map, 
         daily_game_data, roster_data) = result[:5]
        
        print(f"✅ Data initialized - checking pitcher availability:")
        
        # Check available pitchers
        pitchers = []
        for pid, pdata in master_player_data.items():
            roster_info = pdata.get('roster_info', {})
            if roster_info.get('type') == 'pitcher':
                pitchers.append({
                    'id': pid,
                    'fullName': roster_info.get('fullName', ''),
                    'fullName_resolved': roster_info.get('fullName_resolved', ''),
                    'team': roster_info.get('team', ''),
                    'name': roster_info.get('name', '')
                })
        
        print(f"   Found {len(pitchers)} pitchers in master data")
        
        # Test specific pitchers that were failing
        test_pitchers = [
            "Blake Snell",
            "Gerrit Cole", 
            "Andrés Muñoz",
            "José Alvarado"  # This one works
        ]
        
        for test_pitcher in test_pitchers:
            print(f"\n🔍 Searching for: '{test_pitcher}'")
            
            # Find exact matches
            exact_matches = []
            for pitcher in pitchers:
                for field in ['fullName', 'fullName_resolved', 'name']:
                    value = pitcher.get(field, '')
                    if value and value.lower() == test_pitcher.lower():
                        exact_matches.append((field, pitcher))
                        break
            
            if exact_matches:
                print(f"   ✅ Exact matches found: {len(exact_matches)}")
                for field, pitcher in exact_matches:
                    print(f"      Match via {field}: {pitcher['fullName']} ({pitcher['team']})")
            else:
                print(f"   ❌ No exact matches found")
                
                # Look for partial matches
                partial_matches = []
                test_lower = test_pitcher.lower()
                for pitcher in pitchers:
                    for field in ['fullName', 'fullName_resolved', 'name']:
                        value = pitcher.get(field, '').lower()
                        if value and (test_lower in value or value in test_lower):
                            partial_matches.append((field, pitcher))
                
                if partial_matches:
                    print(f"   💡 Partial matches found: {len(partial_matches)}")
                    for field, pitcher in partial_matches[:5]:  # Show first 5
                        print(f"      Partial via {field}: {pitcher['fullName']} ({pitcher['team']})")
                else:
                    print(f"   ❌ No partial matches found")
        
        # Show some sample pitcher names to understand the naming pattern
        print(f"\n📋 Sample pitcher names (first 10):")
        for i, pitcher in enumerate(pitchers[:10]):
            print(f"   {i+1}. fullName: '{pitcher['fullName']}' | resolved: '{pitcher['fullName_resolved']}' | team: {pitcher['team']}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_pitcher_lookup()