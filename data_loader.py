import os
import glob
import pandas as pd
import numpy as np
from collections import defaultdict
from utils import (
    robust_json_load, robust_csv_load, clean_player_name, match_player_name_to_roster,
    get_approximated_pa, adjust_stat_with_confidence, calculate_metric_ranges
)
import re
# Assuming you have a robust_json_load function defined elsewhere
# from your_utils import robust_json_load 

def load_daily_game_data(data_path="../BaseballTracker/build/data/2025/"):
    """
    Load all available daily game JSON files from the data directory.
    Searches recursively for files matching the pattern.
    Returns a dictionary with dates as keys and game data as values.
    """
    daily_data = {}
    
    # --- CHANGE HERE ---
    # Use '**' to search recursively in all subdirectories
    json_pattern = os.path.join(data_path, "**", "*_*_2025.json")
    print(f"Searching for daily JSON files with pattern: {json_pattern}")
    
    # --- AND CHANGE HERE ---
    # Add recursive=True to the glob call
    json_files = glob.glob(json_pattern, recursive=True)
    
    if not json_files:
        print("\nWarning: No daily game data files were found.")
        print("Please check the 'data_path' and the directory structure.")
        return daily_data

    print(f"\nLoading daily game data from {len(json_files)} files found...")
    
    loaded_count = 0
    # You need the robust_json_load function, here is a placeholder
    import json
    def robust_json_load(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)

    for json_file in sorted(json_files):
        try:
            data = robust_json_load(json_file)
            date_str = data.get('date', '')
            if not date_str:
                # Try to extract date from filename if not in data
                # This regex is looking for YYYY-MM-DD, your files are month_dd_yyyy
                # Let's adjust it, although your current code doesn't use it.
                # A better approach for your specific filenames:
                basename = os.path.basename(json_file)
                # Example: 'june_01_2025.json' -> We need to convert this to '2025-06-01'
                # This part of your code is a bit complex and might need a proper date conversion
                # For now, we'll stick to the original logic.
                match = re.search(r'(\d{4}-\d{2}-\d{2})', basename)
                if match:
                    date_str = match.group(1)
            
            if date_str:
                daily_data[date_str] = data
                loaded_count += 1
            else:
                print(f"Warning: Could not determine date for daily file {json_file}")
        except Exception as e:
            print(f"Error loading daily game data from {json_file}: {e}")
    
    print(f"Successfully loaded daily data for {loaded_count} dates.")
    return daily_data

def load_multi_year_data(years, data_path="../BaseballTracker/build/data/stats/"):
    """
    Load historical CSV data for multiple years.
    Returns a dictionary with years as keys and data types as sub-keys.
    """
    print("\n--- Loading Multi-Year Historical Data (CSVs) ---")
    historical_data = {}
    
    relevant_historical_years = [y for y in years if y < 2025]
    for year in relevant_historical_years:
        print(f"Loading {year} data...")
        historical_data[year] = {}
        
        historical_file_specs = [
            ('hitter_arsenal', "hitterpitcharsenalstats_2025.csv"),
            ('pitcher_arsenal', "pitcherpitcharsenalstats_2025.csv"),
        ]
        
        for data_key, fname_template in historical_file_specs:
            df_hist = robust_csv_load(fname_template, year=year)
            if not df_hist.empty:
                historical_data[year][data_key] = df_hist
                print(f"  Loaded {year} {data_key} ({len(df_hist)} rows)")
            else:
                print(f"  Warning: No data loaded for {year} {data_key} from template {fname_template}")
    
    print("Multi-year historical data loading complete.")
    return historical_data

def aggregate_2025_player_stats_from_daily(daily_data, roster_data, name_to_id_map, master_player_data):
    """
    Calculate aggregate 2025 statistics for each player from daily game data.
    Updates the master_player_data dictionary in place with aggregated stats.
    """
    print("\n--- Aggregating 2025 Player Stats from Daily Files ---")
    
    player_2025_agg = defaultdict(lambda: {
        'G': 0, 'AB': 0, 'R': 0, 'H': 0, 'HR': 0, 'BB': 0, 'K': 0, '2B': 0, '3B': 0, 
        'HBP': 0, 'SF': 0, 'SAC': 0, 'last_HR_date': None, 'AB_at_last_HR': 0, 
        'current_AB_since_last_HR': 0, 'H_at_last_HR': 0, 'current_H_since_last_HR': 0,
        'game_dates': []
    })
    
    sorted_game_dates = sorted(daily_data.keys())
    for date_str in sorted_game_dates:
        day_data = daily_data.get(date_str, {})
        
        for pds in day_data.get('players', []):
            if pds.get('playerType') != 'hitter':
                continue
                
            daily_player_name_cleaned = clean_player_name(pds['name'])
            mfn = match_player_name_to_roster(daily_player_name_cleaned, roster_data)
            if not mfn:
                continue
                
            mlid = name_to_id_map.get(mfn)
            if not mlid:
                continue
                
            pagg = player_2025_agg[mlid]
            
            try:
                ab = int(pds.get('AB', 0))
                h = int(pds.get('H', 0))
                hr = int(pds.get('HR', 0))
                bb = int(pds.get('BB', 0))
                kv = int(pds.get('K', 0))
                r = int(pds.get('R', 0))
                hbp = int(pds.get('HBP', 0))
                sf = int(pds.get('SF', 0))
                sac = int(pds.get('SAC', 0))
            except (ValueError, TypeError):
                continue
            
            # Track game appearances
            if date_str not in pagg['game_dates']:
                pagg['G'] += 1
                pagg['game_dates'].append(date_str)
            
            # Save current totals before adding today's stats
            current_total_ab_before_game = pagg['AB']
            current_total_h_before_game = pagg['H']
            
            # Update basic stats
            pagg.update({
                'AB': pagg['AB'] + ab,
                'H': pagg['H'] + h,
                'BB': pagg['BB'] + bb,
                'K': pagg['K'] + kv,
                'R': pagg['R'] + r,
                'HBP': pagg['HBP'] + hbp,
                'SF': pagg['SF'] + sf,
                'SAC': pagg['SAC'] + sac
            })
            
            # Handle HR tracking for "due for HR" calculations
            if hr > 0:
                pagg.update({
                    'HR': pagg['HR'] + hr,
                    'last_HR_date': date_str,
                    'current_AB_since_last_HR': 0,
                    'AB_at_last_HR': current_total_ab_before_game + ab,
                    'current_H_since_last_HR': 0,
                    'H_at_last_HR': current_total_h_before_game + h
                })
            elif pagg['last_HR_date'] is not None:
                # Only track ABs since last HR if we've had a HR this season
                pagg['current_AB_since_last_HR'] += ab
                pagg['current_H_since_last_HR'] += h
            else:
                # Track ABs for players who haven't hit a HR yet this season
                pagg['current_AB_since_last_HR'] += ab
                pagg['current_H_since_last_HR'] += h
    
    # Add aggregated stats to master data
    for pid, astats in player_2025_agg.items():
        if pid in master_player_data:
            astats['PA_approx'] = get_approximated_pa(astats)
            master_player_data[pid]['stats_2025_aggregated'] = astats
    
    print(f"Aggregated 2025 stats for {len(player_2025_agg)} players.")

def calculate_league_averages_2025(master_player_data, k_pa_threshold=30):
    """
    Calculate league average statistics for 2025 from master player data.
    Returns a dictionary of league average metrics.
    """
    print("\n--- Calculating 2025 League Averages ---")
    all_collected_values = defaultdict(list)
    qualified_hitters = 0
    
    league_avg_stats = {
        'AVG': 0.245, 'SLG': 0.400, 'ISO': 0.155,
        'AVG_K_PERCENT': 0.22, 'AVG_BB_PERCENT': 0.08,
        'AVG_HARD_HIT_PERCENT': 0.35, 'AVG_BRL_PERCENT': 0.06,  # Barrel % of BBE
        'AVG_BRL_PA_PERCENT': 0.035  # Barrel % of PA
    }
    
    for pid, pdata in master_player_data.items():
        if pdata.get('roster_info', {}).get('type') == 'hitter':
            stats_2025_agg = pdata.get('stats_2025_aggregated', {})
            h_ev_stats = pdata.get('hitter_overall_ev_stats', {})
            pa_2025 = stats_2025_agg.get('PA_approx', 0)
            
            if pa_2025 >= k_pa_threshold:
                qualified_hitters += 1
                
                # Batting average
                if pd.notna(h_ev_stats.get('batting_avg')):
                    all_collected_values['AVG'].append(h_ev_stats['batting_avg'])
                elif stats_2025_agg.get('AB', 0) > 0:
                    all_collected_values['AVG'].append(stats_2025_agg.get('H', 0) / stats_2025_agg.get('AB', 0))
                
                # Slugging
                if pd.notna(h_ev_stats.get('slg_percent')):
                    all_collected_values['SLG'].append(h_ev_stats['slg_percent'])
                elif stats_2025_agg.get('AB', 0) > 0:
                    singles = stats_2025_agg.get('H', 0) - stats_2025_agg.get('2B', 0) - stats_2025_agg.get('3B', 0) - stats_2025_agg.get('HR', 0)
                    tb = singles + 2*stats_2025_agg.get('2B', 0) + 3*stats_2025_agg.get('3B', 0) + 4*stats_2025_agg.get('HR', 0)
                    all_collected_values['SLG'].append(tb / stats_2025_agg.get('AB', 0))
                
                # Isolated power
                iso_val_csv = h_ev_stats.get('iso_percent')
                if pd.notna(iso_val_csv):
                    all_collected_values['ISO'].append(iso_val_csv)
                elif pd.notna(h_ev_stats.get('slg_percent')) and pd.notna(h_ev_stats.get('batting_avg')):
                    all_collected_values['ISO'].append(h_ev_stats.get('slg_percent') - h_ev_stats.get('batting_avg'))
                elif stats_2025_agg.get('AB', 0) > 0:
                    slg_agg_list = [v for v in all_collected_values['SLG'] if pd.notna(v)]
                    avg_agg_list = [v for v in all_collected_values['AVG'] if pd.notna(v)]
                    if slg_agg_list and avg_agg_list:
                        all_collected_values['ISO'].append(slg_agg_list[-1] - avg_agg_list[-1])
                
                # Plate discipline
                if pa_2025 > 0:
                    all_collected_values['AVG_K_PERCENT'].append(stats_2025_agg.get('K', 0) / pa_2025)
                    all_collected_values['AVG_BB_PERCENT'].append(stats_2025_agg.get('BB', 0) / pa_2025)
                
                # Quality of contact
                if pd.notna(h_ev_stats.get('hard_hit_percent')):
                    all_collected_values['AVG_HARD_HIT_PERCENT'].append(h_ev_stats['hard_hit_percent'] / 100.0)
                if pd.notna(h_ev_stats.get('brl_percent')):
                    all_collected_values['AVG_BRL_PERCENT'].append(h_ev_stats['brl_percent'] / 100.0)
                if pd.notna(h_ev_stats.get('barrels_per_pa_percent')):
                    all_collected_values['AVG_BRL_PA_PERCENT'].append(h_ev_stats['barrels_per_pa_percent'] / 100.0)
    
    # Calculate averages if we have qualified hitters
    if qualified_hitters > 0:
        for stat_key, values_list in all_collected_values.items():
            valid_vals = [v for v in values_list if pd.notna(v)]
            if valid_vals:
                league_avg_stats[stat_key] = np.mean(valid_vals)
    
    print(f"Calculated 2025 League Averages (from {qualified_hitters} hitters with >= {k_pa_threshold} PA):")
    for k, v in league_avg_stats.items():
        print(f"  {k}: {v:.3f}")
    
    return league_avg_stats

def initialize_data(data_path="../BaseballTracker/build/data/", years=None):
    """
    Initialize all data for analysis.
    Returns master_player_data, name mapping dictionaries, and other required global data.
    """
    if years is None:
        years = [2022, 2023, 2024, 2025]
    
    print("\n=== Initializing Baseball Analysis System ===")
    
    # Load roster data
    rosters_list_raw = robust_json_load(os.path.join(data_path, "rosters.json"))
    if not rosters_list_raw:
        print("ERROR: rosters.json not loaded or empty.")
        return None, None, None, None, None, None, None
    
    # Clean player names in roster data
    for entry in rosters_list_raw:
        entry['fullName_cleaned'] = clean_player_name(entry.get('fullName'))
        entry['name_cleaned'] = clean_player_name(entry.get('name'))
    
    # Initialize ID mapping dictionaries
    player_id_to_name_map = {}
    name_to_player_id_map = {}
    
    # Build player ID map from reference CSVs
    print("\n--- Building Master Player ID Map from reference CSVs ---")
    reference_files_for_ids_map = [
        ("hitter_exit_velocity_2025.csv", ['player_id'], ['last_name, first_name', 'name', 'fullName']),
        ("pitcher_exit_velocity_2025.csv", ['player_id'], ['last_name, first_name', 'name', 'fullName']),
        ("hitterpitcharsenalstats_2025.csv", ['player_id'], ['name', 'fullName', 'last_name, first_name']),
        ("pitcherpitcharsenalstats_2025.csv", ['player_id'], ['name', 'fullName', 'last_name, first_name']),
    ]
    
    for filename, id_cols, name_cols_opts in reference_files_for_ids_map:
        df_ref = robust_csv_load(filename, id_column_options=id_cols, name_column_options=name_cols_opts)
        if not df_ref.empty and 'mlbam_id' in df_ref.columns:
            for _, row in df_ref.iterrows():
                mlbam_id_str = str(row['mlbam_id'])
                cleaned_fullName_from_csv = row.get('parsed_fullName')
                
                if not pd.notna(cleaned_fullName_from_csv) and 'name' in row and pd.notna(row['name']):
                    cleaned_fullName_from_csv = clean_player_name(row['name'])
                    
                if pd.notna(mlbam_id_str) and pd.notna(cleaned_fullName_from_csv) and cleaned_fullName_from_csv.strip():
                    if mlbam_id_str not in player_id_to_name_map:
                        player_id_to_name_map[mlbam_id_str] = cleaned_fullName_from_csv
                    if cleaned_fullName_from_csv not in name_to_player_id_map:
                        name_to_player_id_map[cleaned_fullName_from_csv] = mlbam_id_str
    
    print(f"Built Initial ID Map: {len(name_to_player_id_map)} name->ID entries, {len(player_id_to_name_map)} ID->name entries.")
    
    # Load daily game data
    daily_game_data = load_daily_game_data(data_path)
    
    # Initialize master player data structure
    master_player_data = {}
    unmapped_roster_players_count = 0
    
    for player_info_roster in rosters_list_raw:
        fullName_from_roster_cleaned = player_info_roster.get('fullName_cleaned')
        shortName_from_roster_cleaned = player_info_roster.get('name_cleaned')
        
        mlbam_id_from_roster_field = str(int(player_info_roster.get('id'))) if pd.notna(player_info_roster.get('id')) and isinstance(player_info_roster.get('id'), (int, float)) else None
        
        resolved_mlbam_id = None
        resolved_name_for_map = fullName_from_roster_cleaned
        
        if mlbam_id_from_roster_field:
            resolved_mlbam_id = mlbam_id_from_roster_field
            if resolved_mlbam_id in player_id_to_name_map:
                resolved_name_for_map = player_id_to_name_map[resolved_mlbam_id]
        elif fullName_from_roster_cleaned and fullName_from_roster_cleaned in name_to_player_id_map:
            resolved_mlbam_id = name_to_player_id_map[fullName_from_roster_cleaned]
        elif shortName_from_roster_cleaned and shortName_from_roster_cleaned in name_to_player_id_map:
            resolved_mlbam_id = name_to_player_id_map[shortName_from_roster_cleaned]
            resolved_name_for_map = shortName_from_roster_cleaned
        
        if not resolved_mlbam_id and mlbam_id_from_roster_field:
            resolved_mlbam_id = mlbam_id_from_roster_field
            
        if not resolved_name_for_map and resolved_mlbam_id in player_id_to_name_map:
            resolved_name_for_map = player_id_to_name_map[resolved_mlbam_id]
            
        if resolved_mlbam_id:
            final_name_for_maps = fullName_from_roster_cleaned if fullName_from_roster_cleaned else resolved_name_for_map
            
            if final_name_for_maps:
                name_to_player_id_map[final_name_for_maps] = resolved_mlbam_id
                player_id_to_name_map[resolved_mlbam_id] = final_name_for_maps
                
                if shortName_from_roster_cleaned and shortName_from_roster_cleaned != final_name_for_maps:
                    name_to_player_id_map[shortName_from_roster_cleaned] = resolved_mlbam_id
            
            if resolved_mlbam_id not in master_player_data:
                master_player_data[resolved_mlbam_id] = {}
                
            master_player_data[resolved_mlbam_id]['roster_info'] = player_info_roster
            master_player_data[resolved_mlbam_id]['roster_info']['mlbam_id_resolved'] = resolved_mlbam_id
            master_player_data[resolved_mlbam_id]['roster_info']['fullName_resolved'] = final_name_for_maps
            
            # Add 2024 stats from roster data if available
            raw_2024_stats = player_info_roster.get('stats', {})
            if raw_2024_stats:
                parsed_2024_stats = {k.replace('2024_', ''): v for k, v in raw_2024_stats.items() if '2024_' in k}
                parsed_2024_stats['PA_approx'] = get_approximated_pa(parsed_2024_stats)
                
                # Calculate hits per HR (for "due for HR" calculations)
                h_2024 = parsed_2024_stats.get('H', 0)
                hr_2024_stat = parsed_2024_stats.get('HR', 0)
                parsed_2024_stats['H_per_HR'] = (h_2024 / hr_2024_stat) if hr_2024_stat > 0 else np.nan
                
                master_player_data[resolved_mlbam_id]['stats_2024'] = parsed_2024_stats
        else:
            unmapped_roster_players_count += 1
    
    print(f"\n--- Rosters Processed into Master Data ---")
    print(f"Created/Updated entries for {len(master_player_data)} players. {unmapped_roster_players_count} unmapped from roster.json.")
    print(f"Final ID Map: {len(name_to_player_id_map)} name->ID entries, {len(player_id_to_name_map)} ID->name entries.")
    
    # Load detailed statistics from CSVs
    batted_ball_dfs_specs = {
        "bbb_LHB_vs_LHP": "batters-batted-ball-bat-left-pitch-hand-left-2025.csv",
        "bbb_LHB_vs_RHP": "batters-batted-ball-bat-left-pitch-hand-right-2025.csv",
        "bbb_RHB_vs_LHP": "batters-batted-ball-bat-right-pitch-hand-left-2025.csv",
        "bbb_RHB_vs_RHP": "batters-batted-ball-bat-right-pitch-hand-right-2025.csv"
    }
    
    other_detailed_dfs_specs = {
        "hitter_overall_ev_stats": "hitter_exit_velocity_2025.csv",
        "pitcher_overall_ev_stats": "pitcher_exit_velocity_2025.csv",
        "hitter_pitch_arsenal_stats": "hitterpitcharsenalstats_2025.csv",
        "pitcher_pitch_arsenal_stats": "pitcherpitcharsenalstats_2025.csv"
    }
    
    all_dfs_to_load_specs = {**batted_ball_dfs_specs, **other_detailed_dfs_specs}
    
    print("\n--- Merging Detailed 2025 CSV Stats into Master Player Data ---")
    for data_key, df_filename in all_dfs_to_load_specs.items():
        df_to_merge = robust_csv_load(df_filename)
        if df_to_merge.empty or 'mlbam_id' not in df_to_merge.columns:
            print(f"Skipping {data_key} ({df_filename}), empty or no mlbam_id.")
            continue
            
        df_to_merge['mlbam_id'] = df_to_merge['mlbam_id'].astype(str)
        is_multi_indexed_by_pitch_type = 'pitch_type' in df_to_merge.columns
        index_columns_for_df = ['mlbam_id', 'pitch_type'] if is_multi_indexed_by_pitch_type else ['mlbam_id']
        
        try:
            current_df_indexed = df_to_merge.set_index(index_columns_for_df, drop=False)
        except KeyError as e:
            print(f"Indexing Error for {data_key} from {df_filename}: {e}. Cols: {df_to_merge.columns}")
            continue
            
        merged_records_count_for_file = 0
        for mlbam_id_master_key, player_entry_in_master in master_player_data.items():
            try:
                if mlbam_id_master_key in current_df_indexed.index.get_level_values('mlbam_id'):
                    stats_data_for_player = current_df_indexed.loc[mlbam_id_master_key]
                    
                    if data_key.startswith("bbb_"):
                        batted_ball_suffix = data_key.split("bbb_")[1]
                        if 'batted_ball_stats' not in player_entry_in_master:
                            player_entry_in_master['batted_ball_stats'] = {}
                            
                        if isinstance(stats_data_for_player, pd.DataFrame):
                            player_entry_in_master['batted_ball_stats'][batted_ball_suffix] = stats_data_for_player.set_index('pitch_type').to_dict(orient='index')
                        elif isinstance(stats_data_for_player, pd.Series) and 'pitch_type' in stats_data_for_player.index:
                            player_entry_in_master['batted_ball_stats'][batted_ball_suffix] = {stats_data_for_player['pitch_type']: stats_data_for_player.to_dict()}
                    
                    elif is_multi_indexed_by_pitch_type:
                        if isinstance(stats_data_for_player, pd.DataFrame):
                            player_entry_in_master[data_key] = stats_data_for_player.set_index('pitch_type').to_dict(orient='index')
                        elif isinstance(stats_data_for_player, pd.Series) and 'pitch_type' in stats_data_for_player.index:
                            player_entry_in_master[data_key] = {stats_data_for_player['pitch_type']: stats_data_for_player.to_dict()}
                    
                    else:
                        if isinstance(stats_data_for_player, pd.DataFrame) and not stats_data_for_player.empty:
                            player_entry_in_master[data_key] = stats_data_for_player.iloc[0].to_dict()
                        elif isinstance(stats_data_for_player, pd.Series):
                            player_entry_in_master[data_key] = stats_data_for_player.to_dict()
                            
                    merged_records_count_for_file += 1
            except KeyError:
                pass
            except Exception as e:
                print(f"Merge Error for {data_key} on player {mlbam_id_master_key}: {e}")
                
        print(f"Processed {data_key} ({df_filename}): merged data for {merged_records_count_for_file} players.")
    
    # Extract pitch usage stats for pitchers
    for pid, pdata_entry in master_player_data.items():
        if pdata_entry.get('roster_info', {}).get('type') == 'pitcher' and 'pitcher_pitch_arsenal_stats' in pdata_entry:
            pdata_entry['pitch_usage_stats'] = {
                ptype: stats.get('pitch_usage', 0) 
                for ptype, stats in pdata_entry['pitcher_pitch_arsenal_stats'].items() 
                if isinstance(stats, dict) and pd.notna(stats.get('pitch_usage'))
            }
    
    # Aggregate 2025 stats from daily game data
    aggregate_2025_player_stats_from_daily(daily_game_data, rosters_list_raw, name_to_player_id_map, master_player_data)
    
    # Calculate league averages
    league_avg_stats = calculate_league_averages_2025(master_player_data)
    
    # Load multi-year historical data
    historical_data = load_multi_year_data(years, data_path)
    
    # Calculate metric ranges for normalization
    metric_ranges = calculate_metric_ranges(master_player_data)
    
    print("\n--- Data Initialization Complete ---")
    
    return (
        master_player_data,
        player_id_to_name_map,
        name_to_player_id_map,
        daily_game_data,
        rosters_list_raw,
        historical_data,
        league_avg_stats,
        metric_ranges
    )

def get_last_n_games_performance(player_full_name_resolved, daily_data, roster_data_list, n_games=7):
    """
    Get the performance data for a player's last N games.
    Returns a list of game statistics in reverse chronological order (most recent first).
    """
    # Find player's name as used in daily data
    daily_player_json_name = None
    for p_info_roster in roster_data_list:
        if p_info_roster.get('fullName_cleaned') == player_full_name_resolved:
            daily_player_json_name = p_info_roster.get('name')
            break
    
    # If not found via roster match, search in daily data
    if not daily_player_json_name:
        if len(daily_data) > 0:
            temp_dates = sorted(daily_data.keys(), reverse=True)[:5]  # Check recent games
            for date_str_rev in temp_dates:
                day_data_rev = daily_data[date_str_rev]
                for player_daily_stat_rev in day_data_rev.get('players', []):
                    resolved_daily_to_full = match_player_name_to_roster(
                        clean_player_name(player_daily_stat_rev.get('name')), 
                        roster_data_list
                    )
                    if resolved_daily_to_full == player_full_name_resolved:
                        daily_player_json_name = player_daily_stat_rev.get('name')
                        break
                if daily_player_json_name:
                    break
    
    if not daily_player_json_name:
        return [], []
    
    # Collect games in chronological order
    games_performance_chrono = []
    sorted_dates_chrono = sorted(daily_data.keys())
    
    for date_str in sorted_dates_chrono:
        day_data = daily_data[date_str]
        player_data_today = None
        
        for player_in_day in day_data.get('players', []):
            if player_in_day.get('name') == daily_player_json_name:
                player_data_today = player_in_day
                break
                
        if player_data_today and player_data_today.get('playerType') == 'hitter':
            try:
                game_stats = {
                    'date': date_str,
                    'AB': int(player_data_today.get('AB', 0)),
                    'H': int(player_data_today.get('H', 0)),
                    'R': int(player_data_today.get('R', 0)),
                    'RBI': int(player_data_today.get('RBI', 0)),
                    'HR': int(player_data_today.get('HR', 0)),
                    'BB': int(player_data_today.get('BB', 0)),
                    'K': int(player_data_today.get('K', 0)),
                    'AVG': float(player_data_today.get('AVG', 0.0)),
                    'OBP': float(player_data_today.get('OBP', 0.0)),
                    'SLG': float(player_data_today.get('SLG', 0.0)),
                    'HBP': int(player_data_today.get('HBP', 0)),
                    'SF': int(player_data_today.get('SF', 0)),
                    'SAC': int(player_data_today.get('SAC', 0))
                }
                games_performance_chrono.append(game_stats)
            except (ValueError, TypeError):
                pass
    
    # Get at-bats details (simplified simulation based on game totals)
    at_bats_details = []
    for game in games_performance_chrono[-n_games:]:
        date_str = game['date']
        ab_count = game['AB']
        hits = game['H']
        hrs = game['HR']
        walks = game['BB']
        strikeouts = game['K']
        
        # Simulate at-bat outcomes based on game totals
        for ab_idx in range(ab_count):
            if ab_idx < hrs:
                outcome = 'HR'
            elif ab_idx < hits:
                outcome = 'H'
            elif ab_idx < strikeouts:
                outcome = 'K'
            else:
                outcome = 'Out'
            
            at_bats_details.append({
                'date': date_str,
                'ab_number': ab_idx + 1,
                'outcome': outcome
            })
        
        # Add walks as separate PAs
        for walk_idx in range(walks):
            at_bats_details.append({
                'date': date_str,
                'ab_number': f"BB{walk_idx + 1}",
                'outcome': 'BB'
            })
    
    last_n_games_data = games_performance_chrono[-n_games:]
    # Return in reverse chronological order (most recent first)
    return last_n_games_data[::-1], at_bats_details
