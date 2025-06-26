#!/usr/bin/env python3
"""
Test the comprehensive lookup directly without API.
"""

import sys
import os

# Ensure we can import from the local directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_direct_lookup():
    """Test the comprehensive lookup chain directly"""
    
    try:
        from data_loader import initialize_data, get_last_n_games_performance
        from enhanced_data_handler import EnhancedDataHandler
        
        print("🔄 Initializing data...")
        
        # Initialize data
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
        
        # Test a known PHI batter
        print(f"\n🔍 Looking for PHI batters...")
        phi_batters = [r for r in roster_data if r.get('team') == 'PHI' and r.get('type') == 'hitter']
        print(f"   Found {len(phi_batters)} PHI hitters")
        
        if phi_batters:
            test_batter = phi_batters[0]
            batter_name = test_batter.get('fullName', 'Unknown')
            print(f"\n🎯 Testing batter: {batter_name}")
            
            # Test the comprehensive lookup directly
            print(f"   🔄 Calling get_last_n_games_performance...")
            try:
                games, at_bats = get_last_n_games_performance(
                    batter_name, 7, roster_data, daily_game_data
                )
                
                print(f"   📊 Direct lookup results:")
                print(f"      Games found: {len(games)}")
                print(f"      At-bats found: {len(at_bats)}")
                
                if games:
                    print(f"   ✅ SUCCESS - Recent games found!")
                    for i, game in enumerate(games[:3]):
                        print(f"      Game {i+1}: {game.get('date')} - {game.get('H')}/{game.get('AB')} (.{int(game.get('AVG', 0)*1000):03d})")
                else:
                    print(f"   ❌ NO GAMES FOUND - This explains the FALLBACK")
                
            except Exception as e:
                print(f"   ❌ Error in direct lookup: {e}")
                import traceback
                traceback.print_exc()
            
            # Test the enhanced data handler
            print(f"\n🔧 Testing EnhancedDataHandler...")
            try:
                handler = EnhancedDataHandler(
                    master_player_data=master_player_data,
                    league_avg_stats={},
                    metric_ranges={},
                    roster_data=roster_data,
                    daily_game_data=daily_game_data
                )
                
                print(f"   ✅ Handler created successfully")
                
                # Find this batter's ID
                batter_id = None
                for pid, pdata in master_player_data.items():
                    roster_info = pdata.get('roster_info', {})
                    if roster_info.get('fullName') == batter_name:
                        batter_id = pid
                        break
                
                if batter_id:
                    print(f"   🔍 Found batter ID: {batter_id}")
                    
                    # Test the batter performance function
                    recent_perf = handler._get_recent_batter_performance(batter_id)
                    
                    if recent_perf:
                        print(f"   ✅ Recent performance found!")
                        print(f"      Data source: {recent_perf.get('data_source', 'unknown')}")
                        print(f"      Games: {recent_perf.get('total_games', 0)}")
                        print(f"      Hits: {recent_perf.get('total_hits', 0)}/{recent_perf.get('total_ab', 0)}")
                    else:
                        print(f"   ❌ No recent performance found")
                else:
                    print(f"   ❌ Could not find batter ID for {batter_name}")
                
            except Exception as e:
                print(f"   ❌ Error testing handler: {e}")
                import traceback
                traceback.print_exc()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running this from the BaseballAPI directory with venv activated")
    except Exception as e:
        print(f"❌ General error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_lookup()