#!/usr/bin/env python3
"""
Focused test for the get_last_n_games_performance lookup chain.
This script directly tests the function that users report is failing.
"""

import sys
import os
import json
import traceback

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_loader import get_last_n_games_performance, initialize_data, validate_comprehensive_lookup_chain
from utils import clean_player_name

def test_comprehensive_lookup_chain():
    """Test the comprehensive lookup chain with various player names"""
    
    print("🚀 Testing Comprehensive Lookup Chain")
    print("=" * 50)
    
    # Initialize data
    print("🔄 Initializing data...")
    try:
        result = initialize_data()
        if not result or len(result) < 5:
            print("❌ Failed to initialize data")
            return
        
        (master_player_data, player_id_to_name_map, name_to_player_id_map, 
         daily_game_data, roster_data) = result[:5]
        
        print(f"✅ Data initialized:")
        print(f"   Master players: {len(master_player_data)}")
        print(f"   Roster entries: {len(roster_data)}")
        print(f"   Daily data dates: {len(daily_game_data)}")
        
    except Exception as e:
        print(f"❌ Error initializing data: {e}")
        traceback.print_exc()
        return
    
    # Test cases - focus on players that should exist
    print(f"\n📋 Available teams in roster data:")
    teams = set()
    hitters_by_team = {}
    
    for entry in roster_data:
        team = entry.get('team', 'UNK')
        player_type = entry.get('type', 'unknown')
        if team != 'UNK':
            teams.add(team)
            if player_type == 'hitter':
                if team not in hitters_by_team:
                    hitters_by_team[team] = []
                hitters_by_team[team].append(entry)
    
    print(f"   Teams found: {sorted(list(teams))}")
    
    # Test with players from a specific team
    test_team = 'SEA'  # Seattle Mariners
    if test_team in hitters_by_team:
        print(f"\n🎯 Testing {test_team} hitters:")
        team_hitters = hitters_by_team[test_team][:5]  # Test first 5
        
        for hitter in team_hitters:
            fullname = hitter.get('fullName', '')
            name = hitter.get('name', '')
            
            print(f"\n🔍 Testing: {fullname}")
            print(f"   Roster name field: '{name}'")
            print(f"   Team: {hitter.get('team')}")
            
            # Test the validation function first
            try:
                success, roster_entry, daily_name, notes = validate_comprehensive_lookup_chain(
                    fullname, roster_data, daily_game_data
                )
                
                print(f"   Validation result: {success}")
                for note in notes:
                    print(f"     {note}")
                
                if success:
                    print(f"   ✅ Validation passed - should find games")
                else:
                    print(f"   ❌ Validation failed - should show FALLBACK")
                
            except Exception as e:
                print(f"   ❌ Validation error: {e}")
                traceback.print_exc()
            
            # Test the actual lookup function
            try:
                print(f"   🔄 Calling get_last_n_games_performance...")
                games, at_bats = get_last_n_games_performance(
                    fullname, 7, roster_data, daily_game_data
                )
                
                print(f"   📊 Results:")
                print(f"     Games found: {len(games)}")
                print(f"     At-bats found: {len(at_bats)}")
                
                if len(games) > 0:
                    print(f"   ✅ SUCCESS - found {len(games)} games")
                    # Show sample games
                    for i, game in enumerate(games[:3]):
                        print(f"     Game {i+1}: {game.get('date')} - {game.get('H')}/{game.get('AB')} ({game.get('HR')} HR)")
                else:
                    print(f"   ❌ FAILED - no games found (should trigger FALLBACK)")
                
            except Exception as e:
                print(f"   ❌ Lookup error: {e}")
                traceback.print_exc()
    
    else:
        print(f"❌ Team {test_team} not found in roster data")
    
    # Test edge cases
    print(f"\n🔍 Testing Edge Cases:")
    
    edge_cases = [
        "José Alvarado",  # Accented characters
        "Andrés Muñoz",   # Accented characters
        "Cal Raleigh",    # Should be common
        "Julio Rodríguez", # Accented characters
        "NonExistent Player",  # Should fail
    ]
    
    for test_name in edge_cases:
        print(f"\n   Testing: '{test_name}'")
        
        try:
            # Quick validation
            success, _, _, notes = validate_comprehensive_lookup_chain(
                test_name, roster_data, daily_game_data
            )
            
            if success:
                print(f"     ✅ Validation passed")
            else:
                print(f"     ❌ Validation failed: {notes[-1] if notes else 'Unknown'}")
            
            # Actual lookup
            games, at_bats = get_last_n_games_performance(
                test_name, 7, roster_data, daily_game_data
            )
            
            if len(games) > 0:
                print(f"     📊 Found {len(games)} games")
            else:
                print(f"     📊 No games found")
                
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    # Test name variations
    print(f"\n🔄 Testing Name Variations:")
    test_player = "José Alvarado"
    variations = [
        test_player,
        "Jose Alvarado",  # Without accent
        clean_player_name(test_player),
        test_player.upper(),
        test_player.lower(),
    ]
    
    for variation in variations:
        print(f"\n   Testing variation: '{variation}'")
        try:
            games, at_bats = get_last_n_games_performance(
                variation, 7, roster_data, daily_game_data
            )
            
            if len(games) > 0:
                print(f"     ✅ SUCCESS - found {len(games)} games")
            else:
                print(f"     ❌ FAILED - no games found")
                
        except Exception as e:
            print(f"     ❌ Error: {e}")

def analyze_daily_data_structure():
    """Analyze the structure of daily data to understand naming patterns"""
    
    print("\n🔍 Analyzing Daily Data Structure")
    print("=" * 40)
    
    try:
        result = initialize_data()
        if not result or len(result) < 5:
            print("❌ Failed to initialize data")
            return
        
        daily_game_data = result[3]
        roster_data = result[4]
        
        print(f"📅 Daily data dates available: {len(daily_game_data)}")
        
        if daily_game_data:
            # Get the most recent date
            recent_date = max(daily_game_data.keys())
            recent_data = daily_game_data[recent_date]
            
            print(f"📊 Analyzing most recent date: {recent_date}")
            
            players_in_daily = recent_data.get('players', [])
            print(f"   Players in daily data: {len(players_in_daily)}")
            
            # Show sample of daily player names
            print(f"\n   Sample daily player names:")
            hitters_in_daily = [p for p in players_in_daily if p.get('playerType') == 'hitter']
            for i, player in enumerate(hitters_in_daily[:10]):
                name = player.get('name', 'Unknown')
                team = player.get('team', 'UNK')
                print(f"     {i+1}. '{name}' ({team})")
            
            # Compare with roster names
            print(f"\n   Sample roster fullNames:")
            hitters_in_roster = [r for r in roster_data if r.get('type') == 'hitter']
            for i, roster_entry in enumerate(hitters_in_roster[:10]):
                fullname = roster_entry.get('fullName', 'Unknown')
                name = roster_entry.get('name', 'Unknown')
                team = roster_entry.get('team', 'UNK')
                print(f"     {i+1}. fullName: '{fullname}' -> name: '{name}' ({team})")
            
            # Look for potential mismatches
            print(f"\n🔍 Looking for potential name mismatches...")
            
            daily_names = set(p.get('name', '') for p in hitters_in_daily)
            roster_names = set(r.get('name', '') for r in hitters_in_roster)
            
            print(f"   Unique daily names: {len(daily_names)}")
            print(f"   Unique roster names: {len(roster_names)}")
            
            names_in_roster_not_daily = roster_names - daily_names
            names_in_daily_not_roster = daily_names - roster_names
            
            if names_in_roster_not_daily:
                print(f"   ⚠️  Roster names NOT in daily data ({len(names_in_roster_not_daily)} names):")
                for name in sorted(list(names_in_roster_not_daily))[:10]:
                    print(f"     - '{name}'")
            
            if names_in_daily_not_roster:
                print(f"   ⚠️  Daily names NOT in roster data ({len(names_in_daily_not_roster)} names):")
                for name in sorted(list(names_in_daily_not_roster))[:10]:
                    print(f"     - '{name}'")
            
            common_names = roster_names & daily_names
            print(f"   ✅ Common names: {len(common_names)}")
            
    except Exception as e:
        print(f"❌ Error analyzing daily data: {e}")
        traceback.print_exc()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the comprehensive lookup chain")
    parser.add_argument("--analyze", action="store_true", help="Analyze data structure")
    parser.add_argument("--player", help="Test specific player")
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_daily_data_structure()
    elif args.player:
        # Test specific player
        print(f"🎯 Testing specific player: {args.player}")
        
        try:
            result = initialize_data()
            if result and len(result) >= 5:
                roster_data = result[4]
                daily_game_data = result[3]
                
                games, at_bats = get_last_n_games_performance(
                    args.player, 7, roster_data, daily_game_data
                )
                
                print(f"📊 Results for '{args.player}':")
                print(f"   Games found: {len(games)}")
                print(f"   At-bats found: {len(at_bats)}")
                
                if games:
                    for game in games[:5]:
                        print(f"   {game.get('date')}: {game.get('H')}/{game.get('AB')} ({game.get('HR')} HR)")
                
        except Exception as e:
            print(f"❌ Error testing player: {e}")
            traceback.print_exc()
    else:
        # Run full tests
        test_comprehensive_lookup_chain()
        analyze_daily_data_structure()

if __name__ == "__main__":
    main()