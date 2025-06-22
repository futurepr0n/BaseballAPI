#!/usr/bin/env python3
"""
Test script to verify field mapping fixes in BaseballAPI.
"""
import sys
sys.path.append('.')

from data_loader import initialize_data
from enhanced_analyzer import enhanced_hr_score_with_missing_data_handling

def test_data_loading():
    """Test if data loading works correctly after fixes"""
    print("Testing data loading...")
    
    try:
        # Initialize data
        result = initialize_data()
        if result[0] is None:
            print("ERROR: Data initialization failed")
            return False
            
        master_player_data, player_id_to_name_map, name_to_player_id_map, daily_game_data, rosters_list_raw, historical_data, league_avg_stats, metric_ranges = result
        
        print(f"✓ Loaded data for {len(master_player_data)} players")
        print(f"✓ Player ID map: {len(player_id_to_name_map)} entries")
        print(f"✓ Daily game data: {len(daily_game_data)} dates")
        
        # Check if some players have aggregated stats
        players_with_2025_stats = 0
        players_with_slg = 0
        players_with_iso = 0
        players_with_ab_since_hr = 0
        
        for pid, pdata in master_player_data.items():
            stats_2025 = pdata.get('stats_2025_aggregated', {})
            if stats_2025:
                players_with_2025_stats += 1
                if stats_2025.get('SLG', 0) > 0:
                    players_with_slg += 1
                if stats_2025.get('ISO', 0) > 0:
                    players_with_iso += 1
                if 'current_AB_since_last_HR' in stats_2025:
                    players_with_ab_since_hr += 1
        
        print(f"✓ Players with 2025 aggregated stats: {players_with_2025_stats}")
        print(f"✓ Players with SLG > 0: {players_with_slg}")
        print(f"✓ Players with ISO > 0: {players_with_iso}")
        print(f"✓ Players with AB since HR tracking: {players_with_ab_since_hr}")
        
        # Test one player's stats in detail
        sample_player = None
        for pid, pdata in master_player_data.items():
            if pdata.get('roster_info', {}).get('type') == 'hitter':
                stats_2025 = pdata.get('stats_2025_aggregated', {})
                if stats_2025.get('AB', 0) > 50:  # Player with significant playing time
                    sample_player = (pid, pdata)
                    break
        
        if sample_player:
            pid, pdata = sample_player
            roster_info = pdata.get('roster_info', {})
            stats_2025 = pdata.get('stats_2025_aggregated', {})
            
            print(f"\n--- Sample Player: {roster_info.get('fullName_resolved', 'Unknown')} ---")
            print(f"AB: {stats_2025.get('AB', 0)}")
            print(f"H: {stats_2025.get('H', 0)}")
            print(f"HR: {stats_2025.get('HR', 0)}")
            print(f"AVG: {stats_2025.get('AVG', 0):.3f}")
            print(f"SLG: {stats_2025.get('SLG', 0):.3f}")
            print(f"ISO: {stats_2025.get('ISO', 0):.3f}")
            print(f"AB since last HR: {stats_2025.get('current_AB_since_last_HR', 'N/A')}")
            print(f"H since last HR: {stats_2025.get('current_H_since_last_HR', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"ERROR in data loading test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_data_loading()
    if success:
        print("\n✅ Data loading tests PASSED!")
    else:
        print("\n❌ Data loading tests FAILED!")
        sys.exit(1)