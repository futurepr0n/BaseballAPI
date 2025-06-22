#!/usr/bin/env python3
"""
Diagnostic script to check what pitcher data is actually loaded in BaseballAPI
This will help identify why all pitchers return the same default stats
"""

import json
import os
from data_loader import initialize_data

def diagnose_pitcher_data():
    """Check what pitcher data is actually available"""
    
    print("🔍 Diagnosing Pitcher Data in BaseballAPI")
    print("=" * 60)
    
    # Initialize data the same way the API does
    try:
        print("📊 Initializing data...")
        data = initialize_data()
        master_player_data = data['master_player_data']
        print(f"✅ Loaded data for {len(master_player_data)} players")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # Test specific pitchers from our batch analysis
    test_pitchers = [
        "Merrill Kelly",
        "Carson Palmquist", 
        "Noah Cameron",
        "Dylan Cease",
        "Griffin Canning"
    ]
    
    print(f"\n🎯 Checking {len(test_pitchers)} test pitchers...")
    
    for pitcher_name in test_pitchers:
        print(f"\n📋 Analyzing: {pitcher_name}")
        print("-" * 40)
        
        # Find pitcher in master data
        pitcher_found = False
        pitcher_data = None
        
        for pid, pdata in master_player_data.items():
            roster_info = pdata.get('roster_info', {})
            if roster_info.get('type') == 'pitcher':
                names_to_check = [
                    roster_info.get('fullName_resolved', ''),
                    roster_info.get('fullName_cleaned', ''),
                    roster_info.get('name_cleaned', ''),
                    roster_info.get('name', '')
                ]
                
                for name in names_to_check:
                    if name and name.lower() == pitcher_name.lower():
                        pitcher_found = True
                        pitcher_data = pdata
                        print(f"   ✅ Found pitcher ID: {pid}")
                        print(f"   📛 Full name: {roster_info.get('fullName_resolved')}")
                        print(f"   🏠 Team: {roster_info.get('team')}")
                        break
                
                if pitcher_found:
                    break
        
        if not pitcher_found:
            print(f"   ❌ Pitcher not found in master data")
            continue
        
        # Check what data is available for this pitcher
        print(f"   📊 Available data sections:")
        for key in pitcher_data.keys():
            print(f"      - {key}")
        
        # Check 2025 stats specifically
        stats_2025 = pitcher_data.get('stats_2025_aggregated', {})
        print(f"   📈 2025 stats available: {len(stats_2025)} fields")
        
        if stats_2025:
            print(f"   📈 2025 stats fields:")
            for field, value in stats_2025.items():
                print(f"      - {field}: {value}")
        else:
            print(f"   ❌ No 2025 stats found")
        
        # Check for other relevant data
        other_data = {
            'pitcher_pitch_arsenal_stats': pitcher_data.get('pitcher_pitch_arsenal_stats', {}),
            'pitch_usage_stats': pitcher_data.get('pitch_usage_stats', {}),
            'pitcher_overall_ev_stats': pitcher_data.get('pitcher_overall_ev_stats', {})
        }
        
        for data_type, data_dict in other_data.items():
            if data_dict:
                print(f"   📊 {data_type}: {len(data_dict)} fields")
            else:
                print(f"   ❌ {data_type}: Empty")
    
    # Summary analysis
    print("\n" + "=" * 60)
    print("📊 SUMMARY ANALYSIS")
    print("=" * 60)
    
    # Count total pitchers and how many have stats
    total_pitchers = 0
    pitchers_with_2025_stats = 0
    
    for pid, pdata in master_player_data.items():
        roster_info = pdata.get('roster_info', {})
        if roster_info.get('type') == 'pitcher':
            total_pitchers += 1
            stats_2025 = pdata.get('stats_2025_aggregated', {})
            if stats_2025:
                pitchers_with_2025_stats += 1
    
    print(f"Total pitchers in database: {total_pitchers}")
    print(f"Pitchers with 2025 stats: {pitchers_with_2025_stats}")
    print(f"Percentage with stats: {(pitchers_with_2025_stats/total_pitchers*100):.1f}%")
    
    if pitchers_with_2025_stats == 0:
        print("\n🚨 CRITICAL ISSUE: No pitchers have 2025 stats!")
        print("This explains why all pitchers return default values (ERA: 4.5, WHIP: 1.3)")
        print("\nPossible causes:")
        print("1. Baseball Savant scraping failed")
        print("2. Data files are missing or corrupted") 
        print("3. Data loading process has errors")
        print("4. Field names don't match expected format")
    elif pitchers_with_2025_stats < total_pitchers * 0.5:
        print(f"\n⚠️ WARNING: Only {pitchers_with_2025_stats}/{total_pitchers} pitchers have stats")
        print("Many pitchers will use default fallback values")
    else:
        print(f"\n✅ GOOD: Most pitchers ({pitchers_with_2025_stats}/{total_pitchers}) have stats")

if __name__ == "__main__":
    diagnose_pitcher_data()