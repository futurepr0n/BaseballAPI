#!/usr/bin/env python3
"""
Complete fixed debug version with pitcher trend analysis everywhere including combined reports
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

print("DEBUG: Script starting")

try:
    from utils import (
        find_player_id_by_name,
        clean_player_name,
        match_player_name_to_roster
    )
    print("DEBUG: Imported utils")
    
    from data_loader import (
        initialize_data, 
        get_last_n_games_performance
    )
    print("DEBUG: Imported data_loader")
    
    from analyzer import (
        calculate_recent_trends,
        enhanced_hr_likelihood_score
    )
    print("DEBUG: Imported analyzer")
    
    from reporter import (
        format_prediction_result,
        format_detailed_matchup_report,
        process_matchup_batch_file,
        print_top_predictions
    )
    print("DEBUG: Imported reporter (partial)")
    
    from sort_utils import (
        sort_predictions,
        get_sort_description
    )
    print("DEBUG: Imported sort_utils")
    
    from sorting_help import print_sorting_options
    print("DEBUG: Imported sorting_help")
    
    from filter_utils import (
        filter_predictions,
        print_filter_options
    )
    print("DEBUG: Imported filter_utils")
    
    try:
        from hitter_filters import (
            load_hitters_from_file,
            filter_predictions_by_hitters
        )
        print("DEBUG: Successfully imported hitter_filters")
        hitter_filtering_available = True
    except ImportError:
        print("DEBUG: hitter_filters not available, continuing without hitter filtering")
        hitter_filtering_available = False
except ImportError as e:
    print(f"DEBUG: Import error: {e}")
    sys.exit(1)

def get_last_n_games_performance_pitcher(pitcher_full_name_resolved, daily_data, roster_data_list, n_games=7):
    """
    Get the performance data for a pitcher's last N games including home/away splits.
    Returns a list of game statistics in reverse chronological order (most recent first).
    """
    print(f"DEBUG: Getting pitcher performance for {pitcher_full_name_resolved}")
    
    # Find pitcher's name as used in daily data
    daily_pitcher_json_name = None
    for p_info_roster in roster_data_list:
        if p_info_roster.get('fullName_cleaned') == pitcher_full_name_resolved:
            daily_pitcher_json_name = p_info_roster.get('name')
            break
    
    # If not found via roster match, search in daily data
    if not daily_pitcher_json_name:
        if len(daily_data) > 0:
            temp_dates = sorted(daily_data.keys(), reverse=True)[:5]  # Check recent games
            for date_str_rev in temp_dates:
                day_data_rev = daily_data[date_str_rev]
                for player_daily_stat_rev in day_data_rev.get('players', []):
                    if player_daily_stat_rev.get('playerType') == 'pitcher':
                        resolved_daily_to_full = match_player_name_to_roster(
                            clean_player_name(player_daily_stat_rev.get('name')), 
                            roster_data_list
                        )
                        if resolved_daily_to_full == pitcher_full_name_resolved:
                            daily_pitcher_json_name = player_daily_stat_rev.get('name')
                            break
                if daily_pitcher_json_name:
                    break
    
    if not daily_pitcher_json_name:
        print(f"DEBUG: Could not find pitcher {pitcher_full_name_resolved} in daily data")
        return [], []
    
    print(f"DEBUG: Found pitcher in daily data as: {daily_pitcher_json_name}")
    
    # Collect games in chronological order
    games_performance_chrono = []
    sorted_dates_chrono = sorted(daily_data.keys())
    
    for date_str in sorted_dates_chrono:
        day_data = daily_data[date_str]
        pitcher_data_today = None
        
        # Get game info to determine home/away
        game_info = day_data.get('game_info', {})
        home_team = game_info.get('home_team', '')
        away_team = game_info.get('away_team', '')
        
        for player_in_day in day_data.get('players', []):
            if player_in_day.get('name') == daily_pitcher_json_name and player_in_day.get('playerType') == 'pitcher':
                pitcher_data_today = player_in_day
                break
                
        if pitcher_data_today:
            try:
                # Determine if pitcher is at home or away
                pitcher_team = pitcher_data_today.get('team', '')
                is_home_game = (pitcher_team == home_team)
                
                game_stats = {
                    'date': date_str,
                    'IP': float(pitcher_data_today.get('IP', 0.0)),
                    'H': int(pitcher_data_today.get('H', 0)),
                    'R': int(pitcher_data_today.get('R', 0)),
                    'ER': int(pitcher_data_today.get('ER', 0)),
                    'HR': int(pitcher_data_today.get('HR', 0)),
                    'BB': int(pitcher_data_today.get('BB', 0)),
                    'K': int(pitcher_data_today.get('K', 0)),
                    'ERA': float(pitcher_data_today.get('ERA', 0.0)),
                    'WHIP': float(pitcher_data_today.get('WHIP', 0.0)),
                    'team': pitcher_team,
                    'is_home': is_home_game,
                    'opponent': away_team if is_home_game else home_team
                }
                games_performance_chrono.append(game_stats)
                print(f"DEBUG: Added game {date_str}: {game_stats['IP']} IP, {game_stats['H']} H, {game_stats['HR']} HR, {game_stats['K']} K, Home: {is_home_game}")
            except (ValueError, TypeError) as e:
                print(f"DEBUG: Error processing pitcher data for {date_str}: {e}")
                pass
    
    last_n_games_data = games_performance_chrono[-n_games:]
    print(f"DEBUG: Returning {len(last_n_games_data)} recent pitcher games")
    # Return in reverse chronological order (most recent first)
    return last_n_games_data[::-1], []

def calculate_recent_trends_pitcher(games_performance):
    """
    Calculate performance trends from a pitcher's recent games.
    Returns a dictionary of aggregated stats and trend information.
    """
    if not games_performance:
        print("DEBUG: No pitcher games to analyze")
        return {}
    
    num_games = len(games_performance)
    print(f"DEBUG: Calculating pitcher trends for {num_games} games")
    
    # Calculate totals across all games
    total_ip = sum(g['IP'] for g in games_performance)
    total_h = sum(g['H'] for g in games_performance)
    total_hr = sum(g['HR'] for g in games_performance)
    total_bb = sum(g['BB'] for g in games_performance)
    total_k = sum(g['K'] for g in games_performance)
    total_er = sum(g['ER'] for g in games_performance)
    
    # Separate home/away stats
    home_games = [g for g in games_performance if g['is_home']]
    away_games = [g for g in games_performance if not g['is_home']]
    
    home_stats = {
        'games': len(home_games),
        'h': sum(g['H'] for g in home_games),
        'hr': sum(g['HR'] for g in home_games),
        'k': sum(g['K'] for g in home_games),
        'ip': sum(g['IP'] for g in home_games)
    }
    
    away_stats = {
        'games': len(away_games),
        'h': sum(g['H'] for g in away_games),
        'hr': sum(g['HR'] for g in away_games),
        'k': sum(g['K'] for g in away_games),
        'ip': sum(g['IP'] for g in away_games)
    }
    
    # Calculate averages and rates
    recent_stats = {
        'total_games': num_games,
        'total_ip': total_ip,
        'total_h': total_h,
        'total_hr': total_hr,
        'total_bb': total_bb,
        'total_k': total_k,
        'total_er': total_er,
        'avg_era': np.mean([g['ERA'] for g in games_performance if g['IP'] > 0]) if any(g['IP'] > 0 for g in games_performance) else 0,
        'avg_whip': np.mean([g['WHIP'] for g in games_performance if g['IP'] > 0]) if any(g['IP'] > 0 for g in games_performance) else 0,
        'h_per_9': (total_h / total_ip) * 9 if total_ip > 0 else 0,
        'hr_per_9': (total_hr / total_ip) * 9 if total_ip > 0 else 0,
        'k_per_9': (total_k / total_ip) * 9 if total_ip > 0 else 0,
        'bb_per_9': (total_bb / total_ip) * 9 if total_ip > 0 else 0,
        'h_per_game': total_h / num_games if num_games > 0 else 0,
        'hr_per_game': total_hr / num_games if num_games > 0 else 0,
        'k_per_game': total_k / num_games if num_games > 0 else 0,
        'home_stats': home_stats,
        'away_stats': away_stats
    }
    
    # Calculate home/away per-game averages
    if home_stats['games'] > 0:
        recent_stats['home_h_per_game'] = home_stats['h'] / home_stats['games']
        recent_stats['home_hr_per_game'] = home_stats['hr'] / home_stats['games']
        recent_stats['home_k_per_game'] = home_stats['k'] / home_stats['games']
    else:
        recent_stats['home_h_per_game'] = 0
        recent_stats['home_hr_per_game'] = 0
        recent_stats['home_k_per_game'] = 0
        
    if away_stats['games'] > 0:
        recent_stats['away_h_per_game'] = away_stats['h'] / away_stats['games']
        recent_stats['away_hr_per_game'] = away_stats['hr'] / away_stats['games']
        recent_stats['away_k_per_game'] = away_stats['k'] / away_stats['games']
    else:
        recent_stats['away_h_per_game'] = 0
        recent_stats['away_hr_per_game'] = 0
        recent_stats['away_k_per_game'] = 0
    
    # Calculate trends (first half vs second half)
    if num_games >= 2:
        mid_point = num_games // 2
        recent_half_games = games_performance[:mid_point]  # More recent games
        earlier_half_games = games_performance[mid_point:]  # Earlier games
        
        if recent_half_games and earlier_half_games:
            # ERA trend
            recent_era = np.mean([g['ERA'] for g in recent_half_games if g['IP'] > 0])
            early_era = np.mean([g['ERA'] for g in earlier_half_games if g['IP'] > 0])
            
            if pd.notna(recent_era) and pd.notna(early_era):
                trend_direction = 'improving' if recent_era < early_era else 'declining' if recent_era > early_era else 'stable'
                recent_stats.update({
                    'trend_metric': 'ERA',
                    'trend_recent_val': round(recent_era, 3),
                    'trend_early_val': round(early_era, 3),
                    'trend_direction': trend_direction,
                    'trend_magnitude': abs(recent_era - early_era)
                })
                print(f"DEBUG: Pitcher ERA trend: {trend_direction} ({early_era:.3f} -> {recent_era:.3f})")
            
            # Alternative trend: HR allowed rate
            recent_hr_ip = sum(g['IP'] for g in recent_half_games)
            recent_hr_allowed = sum(g['HR'] for g in recent_half_games)
            recent_hr_rate = (recent_hr_allowed / recent_hr_ip) * 9 if recent_hr_ip > 0 else 0
            
            early_hr_ip = sum(g['IP'] for g in earlier_half_games)
            early_hr_allowed = sum(g['HR'] for g in earlier_half_games)
            early_hr_rate = (early_hr_allowed / early_hr_ip) * 9 if early_hr_ip > 0 else 0
            
            recent_stats.update({
                'hr_rate_trend': {
                    'early_val': round(early_hr_rate, 3),
                    'recent_val': round(recent_hr_rate, 3),
                    'direction': 'improving' if recent_hr_rate < early_hr_rate else 'declining' if recent_hr_rate > early_hr_rate else 'stable',
                    'magnitude': abs(recent_hr_rate - early_hr_rate)
                }
            })
    
    print(f"DEBUG: Pitcher stats summary - Games: {num_games}, ERA: {recent_stats['avg_era']:.3f}, H/game: {recent_stats['h_per_game']:.1f}, HR/game: {recent_stats['hr_per_game']:.1f}, K/game: {recent_stats['k_per_game']:.1f}")
    print(f"DEBUG: Pitcher trend direction: {recent_stats.get('trend_direction', 'N/A')}")
    return recent_stats

def create_predictions_csv_enhanced(predictions, filename=None):
    """
    Enhanced CSV creation with pitcher trend data and home/away splits including hits.
    This replaces the original create_predictions_csv function everywhere.
    """
    if not predictions:
        print("DEBUG: No predictions to save to CSV")
        return None
    
    print(f"DEBUG: Creating enhanced CSV for {len(predictions)} predictions")
    summary_data = []
    
    for rank_index, pred_data in enumerate(predictions):
        print(f"DEBUG: Processing prediction {rank_index + 1} for CSV")
        
        details = pred_data.get('details', {})
        recent_data = pred_data.get('recent_N_games_raw_data', {})
        recent_trends = recent_data.get('trends_summary_obj', {})
        
        # Get pitcher recent data - ADD DEBUG HERE
        pitcher_data = pred_data.get('pitcher_recent_data', {})
        pitcher_trends = pitcher_data.get('trends_summary_obj', {})
        
        print(f"DEBUG: Pitcher data keys for CSV: {list(pitcher_data.keys())}")
        print(f"DEBUG: Pitcher trends keys: {list(pitcher_trends.keys())}")
        print(f"DEBUG: Pitcher trend direction: {pitcher_trends.get('trend_direction', 'NOT_FOUND')}")
        print(f"DEBUG: Pitcher ERA: {pitcher_trends.get('avg_era', 'NOT_FOUND')}")
        print(f"DEBUG: Pitcher H/game: {pitcher_trends.get('h_per_game', 'NOT_FOUND')}")
        
        csv_row = {
            'Rank': rank_index + 1,
            'Batter': pred_data['batter_name'], 
            'Batter_Team': pred_data['batter_team'], 
            'B_Hand': pred_data['batter_hand'],
            'Pitcher': pred_data['pitcher_name'], 
            'Pitcher_Team': pred_data['pitcher_team'], 
            'P_Hand': pred_data['pitcher_hand'],
            'HR_Score': pred_data['score'],
            'PA_2025': details.get('batter_pa_2025', 0),
            'HR_Prob': pred_data['outcome_probabilities']['homerun'],
            'Hit_Prob': pred_data['outcome_probabilities']['hit'],
            'OB_Prob': pred_data['outcome_probabilities']['reach_base'],
            'K_Prob': pred_data['outcome_probabilities']['strikeout'],
            
            # Existing batter columns
            'AB_since_HR': details.get('ab_since_last_hr', 'N/A'), 
            'Exp_AB_HR': details.get('expected_ab_per_hr', 'N/A'), 
            'AB_Due_Score': details.get('due_for_hr_ab_raw_score', 'N/A'),
            'H_since_HR': details.get('h_since_last_hr', 'N/A'), 
            'Exp_H_HR': details.get('expected_h_per_hr', 'N/A'), 
            'H_Due_Score': details.get('due_for_hr_hits_raw_score', 'N/A'),
            'Contact_Trend': details.get('contact_trend', 'N/A'), 
            'Heat_Score': details.get('heating_up_contact_raw_score', 'N/A'), 
            'Cold_Score': details.get('cold_batter_contact_raw_score', 'N/A'),
            'ISO_2024': details.get('iso_2024', 'N/A'),
            'ISO_2025': details.get('iso_2025_adj_for_trend', 'N/A'),
            'ISO_Trend': details.get('iso_trend_2025v2024', 'N/A'),
            'Recent_Trend_Dir': recent_trends.get('trend_direction', 'N/A'),
            'Recent_HR_Rate': recent_trends.get('hr_rate', 'N/A'),
            'Recent_AVG': recent_trends.get('avg_avg', 'N/A'),
            'Recent_Games': recent_trends.get('total_games', 'N/A'),
            
            # NEW PITCHER COLUMNS - Use get() with default values
            'Pitcher_Trend_Dir': pitcher_trends.get('trend_direction', 'N/A'),
            'Pitcher_Recent_ERA': round(pitcher_trends.get('avg_era', 0), 3) if pitcher_trends.get('avg_era') is not None else 'N/A',
            'Pitcher_Recent_WHIP': round(pitcher_trends.get('avg_whip', 0), 3) if pitcher_trends.get('avg_whip') is not None else 'N/A',
            'Pitcher_H_Per_Game': round(pitcher_trends.get('h_per_game', 0), 1) if pitcher_trends.get('h_per_game') is not None else 'N/A',
            'Pitcher_HR_Per_Game': round(pitcher_trends.get('hr_per_game', 0), 1) if pitcher_trends.get('hr_per_game') is not None else 'N/A',
            'Pitcher_K_Per_Game': round(pitcher_trends.get('k_per_game', 0), 1) if pitcher_trends.get('k_per_game') is not None else 'N/A',
            
            # Home totals
            'Pitcher_Home_H_Total': pitcher_trends.get('home_stats', {}).get('h', 'N/A'),
            'Pitcher_Home_HR_Total': pitcher_trends.get('home_stats', {}).get('hr', 'N/A'),
            'Pitcher_Home_K_Total': pitcher_trends.get('home_stats', {}).get('k', 'N/A'),
            
            # Away totals
            'Pitcher_Away_H_Total': pitcher_trends.get('away_stats', {}).get('h', 'N/A'),
            'Pitcher_Away_HR_Total': pitcher_trends.get('away_stats', {}).get('hr', 'N/A'),
            'Pitcher_Away_K_Total': pitcher_trends.get('away_stats', {}).get('k', 'N/A'),
            
            # Home per-game averages
            'Pitcher_Home_H_Per_Game': round(pitcher_trends.get('home_h_per_game', 0), 1) if pitcher_trends.get('home_h_per_game') is not None else 'N/A',
            'Pitcher_Home_HR_Per_Game': round(pitcher_trends.get('home_hr_per_game', 0), 1) if pitcher_trends.get('home_hr_per_game') is not None else 'N/A',
            'Pitcher_Home_K_Per_Game': round(pitcher_trends.get('home_k_per_game', 0), 1) if pitcher_trends.get('home_k_per_game') is not None else 'N/A',
            
            # Away per-game averages
            'Pitcher_Away_H_Per_Game': round(pitcher_trends.get('away_h_per_game', 0), 1) if pitcher_trends.get('away_h_per_game') is not None else 'N/A',
            'Pitcher_Away_HR_Per_Game': round(pitcher_trends.get('away_hr_per_game', 0), 1) if pitcher_trends.get('away_hr_per_game') is not None else 'N/A',
            'Pitcher_Away_K_Per_Game': round(pitcher_trends.get('away_k_per_game', 0), 1) if pitcher_trends.get('away_k_per_game') is not None else 'N/A',
            
            # Game counts
            'Pitcher_Recent_Games': pitcher_trends.get('total_games', 'N/A'),
            'Pitcher_Home_Games': pitcher_trends.get('home_stats', {}).get('games', 'N/A'),
            'Pitcher_Away_Games': pitcher_trends.get('away_stats', {}).get('games', 'N/A')
        }
        
        # Add arsenal analysis metrics if available
        arsenal_summary = details.get('arsenal_analysis', {}).get('overall_summary_metrics', {})
        if arsenal_summary:
            csv_row['H_Wtd_SLG_vs_Ars'] = arsenal_summary.get('hitter_avg_slg', 'N/A')
            csv_row['P_Wtd_SLG_A_w_Ars'] = arsenal_summary.get('pitcher_avg_slg', 'N/A')
        
        # Add component scores
        components = pred_data.get('matchup_components', {})
        for comp_name, comp_value in components.items():
            csv_row[f'Comp_{comp_name}'] = comp_value
        
        summary_data.append(csv_row)
        
        # Debug the first row
        if rank_index == 0:
            print(f"DEBUG: First CSV row pitcher data:")
            for key, val in csv_row.items():
                if 'Pitcher_' in key:
                    print(f"  {key}: {val}")
    
    # Create DataFrame and save to CSV
    df_results = pd.DataFrame(summary_data)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"predictions_enhanced_{timestamp}.csv"
    
    # Debug column names
    pitcher_columns = [col for col in df_results.columns if 'Pitcher_' in col]
    print(f"DEBUG: Pitcher columns in CSV: {pitcher_columns}")
    
    df_results.to_csv(filename, index=False, float_format='%.3f')
    print(f"\nEnhanced results with pitcher trends and hits saved to CSV: {filename}")
    print(f"CSV contains {len(df_results)} rows and {len(df_results.columns)} columns")
    
    return filename

def generate_combined_report_enhanced(all_matchups_data, filename_prefix="combined_analysis"):
    """
    Generate an enhanced combined report for all matchups with pitcher data.
    This replaces the original generate_combined_report function.
    """
    if not all_matchups_data:
        return None
    
    print(f"DEBUG: Generating enhanced combined report for {len(all_matchups_data)} matchups")
    
    # Flatten all predictions into a single list
    all_predictions = []
    for matchup_info in all_matchups_data:
        predictions = matchup_info['predictions']
        print(f"DEBUG: Adding {len(predictions)} predictions from {matchup_info['pitcher_name']} vs {matchup_info['team_abbr']}")
        all_predictions.extend(predictions)
    
    print(f"DEBUG: Total predictions in combined report: {len(all_predictions)}")
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"{filename_prefix}_enhanced_{timestamp}.csv"
    
    # Generate enhanced CSV with pitcher data
    create_predictions_csv_enhanced(all_predictions, csv_filename)
    
    # Print top predictions
    print(f"\n\n--- Combined Top Predictions from All {len(all_matchups_data)} Processed Matchups (Enhanced with Pitcher Data) ---")
    print_top_predictions(all_predictions, limit=20)
    
    return csv_filename

def process_pitcher_vs_team(
    pitcher_name, team_abbr, 
    master_player_data, name_to_player_id_map, daily_game_data, 
    rosters_data, historical_data, league_avg_stats, metric_ranges):
    """
    Enhanced version that includes pitcher recent performance analysis
    """
    print(f"DEBUG: Entering enhanced process_pitcher_vs_team({pitcher_name}, {team_abbr})")
    
    pitcher_id = find_player_id_by_name(pitcher_name, 'pitcher', master_player_data, name_to_player_id_map)
    print(f"DEBUG: Pitcher ID found: {pitcher_id}")
    
    if not pitcher_id or pitcher_id not in master_player_data:
        print(f"ERROR: Pitcher '{pitcher_name}' not found or not in master data.")
        return []
    
    pitcher_master_info = master_player_data[pitcher_id]
    pitcher_roster_info = pitcher_master_info.get('roster_info', {})
    pitcher_resolved_name = pitcher_roster_info.get('fullName_resolved', pitcher_name)
    pitcher_team = pitcher_roster_info.get('team')
    
    print(f"DEBUG: Pitcher resolved name: {pitcher_resolved_name}, team: {pitcher_team}")
    
    # Get pitcher recent performance
    pitcher_games = []
    pitcher_recent_trends = {}
    
    try:
        pitcher_games, _ = get_last_n_games_performance_pitcher(
            pitcher_resolved_name, daily_game_data, rosters_data
        )
        
        if pitcher_games:
            pitcher_recent_trends = calculate_recent_trends_pitcher(pitcher_games)
            print(f"DEBUG: Successfully calculated pitcher trends: {len(pitcher_games)} games")
            print(f"DEBUG: Pitcher trends keys: {list(pitcher_recent_trends.keys())}")
            print(f"DEBUG: Pitcher trend direction: {pitcher_recent_trends.get('trend_direction', 'N/A')}")
        else:
            print(f"DEBUG: No pitcher games found for {pitcher_resolved_name}")
            
    except Exception as e:
        print(f"DEBUG: Error getting pitcher trends: {e}")
        import traceback
        traceback.print_exc()
    
    # Check if team exists
    team_exists = any(p_info.get('roster_info', {}).get('team') == team_abbr 
                     for p_info in master_player_data.values())
    
    if not team_exists and team_abbr:
        print(f"Warning: Opposing team '{team_abbr}' does not appear to be a valid team in the roster data. Analysis might be empty.")
    
    if pitcher_team == team_abbr:
        print(f"Warning: Pitcher {pitcher_resolved_name} is on the same team ({team_abbr}) being analyzed against. Proceeding anyway.")
    
    print(f"\nAnalyzing {pitcher_resolved_name} (Team: {pitcher_team}) vs {team_abbr} hitters...")
    
    if pitcher_recent_trends:
        print(f"Pitcher recent trends: {len(pitcher_games)} games, ERA trend: {pitcher_recent_trends.get('trend_direction', 'N/A')}")
        print(f"  Recent averages - ERA: {pitcher_recent_trends.get('avg_era', 0):.3f}, H/game: {pitcher_recent_trends.get('h_per_game', 0):.1f}, HR/game: {pitcher_recent_trends.get('hr_per_game', 0):.1f}, K/game: {pitcher_recent_trends.get('k_per_game', 0):.1f}")
        home_games = pitcher_recent_trends.get('home_stats', {}).get('games', 0)
        away_games = pitcher_recent_trends.get('away_stats', {}).get('games', 0)
        print(f"  Home/Away split: {home_games} home games, {away_games} away games")
    else:
        print("No pitcher recent trends available")
    
    predictions = []
    hitters_found = 0
    
    for batter_id, batter_data in master_player_data.items():
        batter_roster_info = batter_data.get('roster_info', {})
        
        if batter_roster_info.get('type') == 'hitter' and batter_roster_info.get('team') == team_abbr:
            hitters_found += 1
            batter_full_name = batter_roster_info.get('fullName_resolved', batter_roster_info.get('fullName_cleaned'))
            
            print(f"DEBUG: Processing hitter: {batter_full_name} (ID: {batter_id})")
            
            # Get recent performance
            try:
                batter_games, batter_at_bats = get_last_n_games_performance(
                    batter_full_name, daily_game_data, rosters_data
                )
                print(f"DEBUG: Found {len(batter_games)} recent games for {batter_full_name}")
                
                batter_recent_trends = calculate_recent_trends(batter_games)
                
                # Calculate HR likelihood
                prediction = enhanced_hr_likelihood_score(
                    batter_id, pitcher_id, 
                    master_player_data, historical_data, metric_ranges, league_avg_stats,
                    batter_recent_trends
                )
                
                if prediction and prediction.get('score', 0) > 0:
                    # Add both batter and pitcher recent game data
                    prediction['recent_N_games_raw_data'] = {
                        'games_list': batter_games[:5],  # Store up to 5 recent games
                        'trends_summary_obj': batter_recent_trends,
                        'at_bats': batter_at_bats[:10]  # Store up to 10 recent at-bats
                    }
                    
                    # CRITICAL: Ensure pitcher data is attached properly
                    prediction['pitcher_recent_data'] = {
                        'games_list': pitcher_games[:5],
                        'trends_summary_obj': pitcher_recent_trends
                    }
                    
                    print(f"DEBUG: Added prediction for {batter_full_name} with score {prediction.get('score', 0)}")
                    print(f"DEBUG: Attached pitcher trends: {list(pitcher_recent_trends.keys())}")
                    
                    predictions.append(prediction)
                else:
                    print(f"DEBUG: No valid prediction for {batter_full_name}")
            except Exception as e:
                print(f"ERROR processing hitter {batter_full_name}: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"DEBUG: Found and analyzed {hitters_found} hitters from {team_abbr}. Generated {len(predictions)} predictions.")
    
    # Sort by HR likelihood score
    predictions.sort(key=lambda x: x.get('score', 0), reverse=True)
    return predictions

def analyze_individual_matchup(
    batter_name, pitcher_name,
    master_player_data, name_to_player_id_map, daily_game_data, 
    rosters_data, historical_data, league_avg_stats, metric_ranges):
    """
    Analyze a specific batter vs pitcher matchup.
    Returns a single prediction result.
    """
    print(f"DEBUG: Entering analyze_individual_matchup({batter_name}, {pitcher_name})")
    
    batter_id = find_player_id_by_name(batter_name, 'hitter', master_player_data, name_to_player_id_map)
    pitcher_id = find_player_id_by_name(pitcher_name, 'pitcher', master_player_data, name_to_player_id_map)
    
    print(f"DEBUG: Batter ID: {batter_id}, Pitcher ID: {pitcher_id}")
    
    if not batter_id:
        print(f"ERROR: Batter '{batter_name}' not found.")
        return None
    
    if not pitcher_id:
        print(f"ERROR: Pitcher '{pitcher_name}' not found.")
        return None
    
    if batter_id not in master_player_data or pitcher_id not in master_player_data:
        print("ERROR: One or both players not found in master data.")
        return None
    
    batter_full_name = master_player_data[batter_id].get('roster_info', {}).get('fullName_resolved', batter_name)
    pitcher_full_name = master_player_data[pitcher_id].get('roster_info', {}).get('fullName_resolved', pitcher_name)
    
    # Get recent performance
    try:
        batter_games, batter_at_bats = get_last_n_games_performance(
            batter_full_name, daily_game_data, rosters_data
        )
        
        pitcher_games, _ = get_last_n_games_performance_pitcher(
            pitcher_full_name, daily_game_data, rosters_data
        )
        
        print(f"DEBUG: Found {len(batter_games)} recent games for {batter_full_name}")
        print(f"DEBUG: Found {len(pitcher_games)} recent games for {pitcher_full_name}")
        
        batter_recent_trends = calculate_recent_trends(batter_games)
        pitcher_recent_trends = calculate_recent_trends_pitcher(pitcher_games)
        
        # Calculate HR likelihood
        prediction = enhanced_hr_likelihood_score(
            batter_id, pitcher_id, 
            master_player_data, historical_data, metric_ranges, league_avg_stats,
            batter_recent_trends
        )
        
        if prediction:
            # Add both batter and pitcher recent game data
            prediction['recent_N_games_raw_data'] = {
                'games_list': batter_games,
                'trends_summary_obj': batter_recent_trends,
                'at_bats': batter_at_bats
            }
            
            prediction['pitcher_recent_data'] = {
                'games_list': pitcher_games,
                'trends_summary_obj': pitcher_recent_trends
            }
            
            print(f"DEBUG: Generated prediction with score {prediction.get('score', 0)}")
        else:
            print(f"DEBUG: No prediction generated")
    
    except Exception as e:
        print(f"ERROR processing matchup: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    return prediction

def run_batch_analysis(
    batch_file, master_player_data, name_to_player_id_map, 
    daily_game_data, rosters_data, historical_data, league_avg_stats, metric_ranges,
    sort_by='score', ascending=False, filter_criteria=None, hitters_list=None):
    """
    Process a batch file with multiple matchups.
    Returns a list of matchup results.
    """
    print(f"\n--- Enhanced Batch Pitcher vs Team Analysis Mode from file: {batch_file} ---")
    
    matchups = process_matchup_batch_file(batch_file)
    if not matchups:
        print("No valid matchups found in batch file.")
        return []
    
    print(f"Processing {len(matchups)} matchups from batch file...")
    
    all_matchups_results = []
    for pitcher_name, team_abbr in matchups:
        try:
            print(f"\n--- Processing matchup: {pitcher_name} vs {team_abbr} ---")
            predictions = process_pitcher_vs_team(
                pitcher_name, team_abbr,
                master_player_data, name_to_player_id_map, daily_game_data,
                rosters_data, historical_data, league_avg_stats, metric_ranges
            )
            
            if predictions:
                # Apply specific hitter filtering if provided
                if hitter_filtering_available and hitters_list:
                    filtered_by_hitters = filter_predictions_by_hitters(predictions, hitters_list)
                    print(f"Filtered to {len(filtered_by_hitters)} of {len(predictions)} hitters based on hitters file.")
                    predictions = filtered_by_hitters
                
                # Only proceed if we have predictions after hitter filtering
                if predictions:
                    # Apply any filters
                    if filter_criteria:
                        filtered_predictions = filter_predictions(predictions, filter_criteria)
                        filter_desc = ", ".join([f"{k}={v}" for k, v in filter_criteria.items()])
                        print(f"Applied filters ({filter_desc}): {len(filtered_predictions)} of {len(predictions)} predictions match.")
                        predictions = filtered_predictions
                    
                    # Only proceed if we have predictions after filtering
                    if predictions:
                        # Sort predictions according to specified criteria
                        sorted_predictions = sort_predictions(predictions, sort_by=sort_by, ascending=ascending)
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        csv_filename = f"analysis_enhanced_{pitcher_name.replace(' ', '_')}_{timestamp}.csv"
                        create_predictions_csv_enhanced(sorted_predictions, csv_filename)
                        
                        all_matchups_results.append({
                            'pitcher_name': pitcher_name,
                            'team_abbr': team_abbr,
                            'predictions': sorted_predictions,
                            'csv_filename': csv_filename
                        })
                        
                        # Print top 5 for each matchup
                        sort_desc = get_sort_description(sort_by)
                        order_desc = "ascending" if ascending else "descending"
                        print(f"\n--- Top 5 Predictions: {pitcher_name} vs {team_abbr} (Sorted by {sort_desc}, {order_desc}) ---")
                        for i, pred in enumerate(sorted_predictions[:5], 1):
                            print(format_prediction_result(pred, i, include_details=False))
                            print("-" * 40)
                    else:
                        print(f"No predictions match the filter criteria for {pitcher_name} vs {team_abbr}")
                else:
                    print(f"No predictions match the specified hitters for {pitcher_name} vs {team_abbr}")
            else:
                print(f"No predictions generated for {pitcher_name} vs {team_abbr}")
        except Exception as e:
            print(f"Error processing matchup {pitcher_name} vs {team_abbr}: {e}")
            import traceback
            traceback.print_exc()
    
    # Generate enhanced combined report with pitcher data
    if all_matchups_results:
        print("\nDEBUG: Generating enhanced combined report...")
        generate_combined_report_enhanced(all_matchups_results)
    
    return all_matchups_results

def main():
    """Main entry point for the baseball analysis program."""
    print("DEBUG: Entered main()")
    
    parser = argparse.ArgumentParser(description='Baseball HR Prediction Analysis System with Enhanced Pitcher Analysis')
    
    parser.add_argument('--batch', type=str, help='Process a batch file with multiple matchups')
    parser.add_argument('--team', action='store_true', help='Analyze pitcher vs team matchup')
    parser.add_argument('--individual', action='store_true', help='Analyze individual batter vs pitcher matchup')
    parser.add_argument('--detailed', action='store_true', help='Show detailed analysis information')
    parser.add_argument('--all', action='store_true', help='Show all predictions, not just top ones')
    parser.add_argument('--limit', type=int, default=15, help='Limit the number of predictions displayed')
    parser.add_argument('--data-path', type=str, default='./data/', help='Path to data directory')
    
    # Hitter filtering (only if available)
    if hitter_filtering_available:
        parser.add_argument('--hitters-file', type=str, help='Path to file containing hitter names to analyze')
    
    # Sorting options
    parser.add_argument('--sort', type=str, default='score', 
                       help='Sort predictions by this field (e.g., score, hr, hit, arsenal, recent_avg, due_ab)')
    parser.add_argument('--ascending', action='store_true', help='Sort in ascending order (default is descending)')
    parser.add_argument('--sort-help', action='store_true', help='Display available sorting options')
    
    # Filtering options
    parser.add_argument('--filter-trend', type=str, help='Filter by trend direction (improving, declining, stable)')
    parser.add_argument('--filter-min-score', type=float, help='Filter by minimum score')
    parser.add_argument('--filter-min-hr-prob', type=float, help='Filter by minimum HR probability')
    parser.add_argument('--filter-min-hit-prob', type=float, help='Filter by minimum hit probability')
    parser.add_argument('--filter-max-k-prob', type=float, help='Filter by maximum strikeout probability')
    parser.add_argument('--filter-contact', type=str, help='Filter by contact quality (heating, cold)')
    parser.add_argument('--filter-min-due-ab', type=float, help='Filter by minimum AB-based due factor')
    parser.add_argument('--filter-min-due-hits', type=float, help='Filter by minimum hits-based due factor')
    parser.add_argument('--filter-help', action='store_true', help='Display available filtering options')
    
    parser.add_argument('args', nargs='*', help='Arguments (either "pitcher team" or "batter pitcher")')
    
    args = parser.parse_args()
    print(f"DEBUG: Parsed args: {args}")
    
    # Load specific hitters from file if provided
    hitters_list = None
    if hitter_filtering_available and hasattr(args, 'hitters_file') and args.hitters_file:
        print(f"DEBUG: Loading hitters from {args.hitters_file}")
        hitters_list = load_hitters_from_file(args.hitters_file)
    
    # If sort-help is requested, show sorting options and exit
    if args.sort_help:
        print_sorting_options()
        return 0
        
    # If filter-help is requested, show filtering options and exit
    if args.filter_help:
        print_filter_options()
        return 0
    
    # Build filter criteria from arguments
    filter_criteria = {}
    if args.filter_trend:
        filter_criteria['trend'] = args.filter_trend
    if args.filter_min_score:
        filter_criteria['min_score'] = args.filter_min_score
    if args.filter_min_hr_prob:
        filter_criteria['min_hr_prob'] = args.filter_min_hr_prob
    if args.filter_min_hit_prob:
        filter_criteria['min_hit_prob'] = args.filter_min_hit_prob
    if args.filter_max_k_prob:
        filter_criteria['max_k_prob'] = args.filter_max_k_prob
    if args.filter_contact:
        filter_criteria['contact_trend'] = args.filter_contact
    if args.filter_min_due_ab:
        filter_criteria['min_due_ab'] = args.filter_min_due_ab
    if args.filter_min_due_hits:
        filter_criteria['min_due_hits'] = args.filter_min_due_hits
    
    print("=" * 80)
    print("Baseball Home Run Prediction Analysis System - Enhanced with Pitcher Analysis")
    print("=" * 80)
    
    # Check data directory exists
    if not os.path.exists(args.data_path):
        print(f"ERROR: Data directory '{args.data_path}' not found.")
        print(f"DEBUG: Current working directory: {os.getcwd()}")
        print(f"DEBUG: Directory contents: {os.listdir('.')}")
        return 1
    
    # List data directory contents
    print(f"DEBUG: Data directory contents: {os.listdir(args.data_path)}")
    
    # Initialize data
    print("DEBUG: Initializing data...")
    years = [2022, 2023, 2024, 2025]
    
    try:
        (
            master_player_data,
            player_id_to_name_map,
            name_to_player_id_map,
            daily_game_data,
            rosters_data,
            historical_data,
            league_avg_stats,
            metric_ranges
        ) = initialize_data(args.data_path, years)
        
        print(f"DEBUG: Initialized data: {len(master_player_data)} players, {len(daily_game_data)} daily game dates")
    except Exception as e:
        print(f"ERROR during data initialization: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    if not master_player_data:
        print("ERROR: Failed to initialize data. Exiting.")
        return 1
    
    # Process batch file
    if args.batch:
        print(f"DEBUG: Processing batch file: {args.batch}")
        
        if not os.path.exists(args.batch):
            print(f"ERROR: Batch file '{args.batch}' not found.")
            return 1
        
        try:
            results = run_batch_analysis(
                args.batch,
                master_player_data, name_to_player_id_map, daily_game_data,
                rosters_data, historical_data, league_avg_stats, metric_ranges,
                sort_by=args.sort, ascending=args.ascending,
                filter_criteria=filter_criteria,
                hitters_list=hitters_list if hitter_filtering_available else None
            )
            return 0 if results else 1
        except Exception as e:
            print(f"ERROR during batch analysis: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # Check for sufficient command line arguments
    if len(args.args) < 2:
        print("\nERROR: Insufficient arguments.")
        print("\nUsage examples:")
        print("  Batch mode: python debug_main.py --batch=matchups.txt")
        print("  With specific hitters: python debug_main.py --batch=matchups.txt --hitters-file=hitters.txt")
        print("  Pitcher vs team: python debug_main.py --team 'Pitcher Name' TEAM")
        print("  Individual matchup: python debug_main.py --individual 'Batter Name' 'Pitcher Name'")
        
        # Run a default example
        default_pitcher = "MacKenzie Gore"
        default_team = "SEA"
        print(f"\nRunning default example (e.g., {default_pitcher} vs {default_team})...")
        
        try:
            default_pitcher_id = find_player_id_by_name(default_pitcher, 'pitcher', master_player_data, name_to_player_id_map)
            print(f"DEBUG: Default pitcher ID: {default_pitcher_id}")
            
            if default_pitcher_id:
                predictions = process_pitcher_vs_team(
                    default_pitcher, default_team,
                    master_player_data, name_to_player_id_map, daily_game_data,
                    rosters_data, historical_data, league_avg_stats, metric_ranges
                )
                
                print(f"DEBUG: Default example predictions: {len(predictions) if predictions else 0}")
                
                if predictions:
                    # Apply specific hitter filtering if provided
                    if hitter_filtering_available and hitters_list:
                        filtered_by_hitters = filter_predictions_by_hitters(predictions, hitters_list)
                        print(f"Filtered to {len(filtered_by_hitters)} of {len(predictions)} hitters based on hitters file.")
                        predictions = filtered_by_hitters
                    
                    if predictions:
                        print(f"\n=== Example Output: {default_pitcher} vs {default_team} Hitters (Top 3) ===")
                        for i, pred in enumerate(predictions[:3], 1):
                            print(format_prediction_result(pred, i, include_details=False))
                            print("-" * 70)
                        
                        # Create enhanced CSV for the example
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        example_csv = f"example_enhanced_{timestamp}.csv"
                        create_predictions_csv_enhanced(predictions, example_csv)
                    else:
                        print("No predictions match the specified hitters.")
            else:
                print(f"Default example pitcher '{default_pitcher}' not found in data.")
        except Exception as e:
            print(f"ERROR during default example: {e}")
            import traceback
            traceback.print_exc()
        
        return 1
    
    # Determine mode based on args and flags
    param1, param2 = args.args[0], args.args[1]
    print(f"DEBUG: Command args: param1='{param1}', param2='{param2}'")
    
    try:
        # Handle team matchup (pitcher vs team)
        if args.team or (len(param2) == 3 and param2.isupper()):
            pitcher_name, team_abbr = param1, param2
            print(f"\n--- Enhanced Pitcher vs Team Analysis: {pitcher_name} vs {team_abbr} ---")
            
            predictions = process_pitcher_vs_team(
                pitcher_name, team_abbr,
                master_player_data, name_to_player_id_map, daily_game_data,
                rosters_data, historical_data, league_avg_stats, metric_ranges
            )
            
            print(f"DEBUG: Generated {len(predictions) if predictions else 0} predictions")
            
            if predictions:
                # Apply specific hitter filtering if provided
                if hitter_filtering_available and hitters_list:
                    filtered_by_hitters = filter_predictions_by_hitters(predictions, hitters_list)
                    print(f"Filtered to {len(filtered_by_hitters)} of {len(predictions)} hitters based on hitters file.")
                    predictions = filtered_by_hitters
                
                # Only proceed if we have predictions after hitter filtering
                if predictions:
                    # Apply any additional filters
                    if filter_criteria:
                        filtered_predictions = filter_predictions(predictions, filter_criteria)
                        filter_desc = ", ".join([f"{k}={v}" for k, v in filter_criteria.items()])
                        print(f"Applied filters ({filter_desc}): {len(filtered_predictions)} of {len(predictions)} predictions match.")
                        predictions = filtered_predictions
                    
                    # Only proceed if we have predictions after all filtering
                    if predictions:
                        # Sort predictions according to specified criteria
                        sorted_predictions = sort_predictions(predictions, sort_by=args.sort, ascending=args.ascending)
                        sort_desc = get_sort_description(args.sort)
                        order_desc = "ascending" if args.ascending else "descending"
                        
                        print(f"\n=== Top Predictions: {pitcher_name} vs {team_abbr} (Sorted by {sort_desc}, {order_desc}) ===")
                        
                        display_limit = None if args.all else args.limit
                        print_top_predictions(sorted_predictions, limit=display_limit, detailed=args.detailed)
                        
                        # Create enhanced CSV output
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        csv_filename = f"analysis_enhanced_{pitcher_name.replace(' ', '_')}_vs_{team_abbr}_{timestamp}.csv"
                        create_predictions_csv_enhanced(sorted_predictions, csv_filename)
                    else:
                        print(f"No predictions match the filter criteria for {pitcher_name} vs {team_abbr}")
                else:
                    print(f"No predictions match the specified hitters for {pitcher_name} vs {team_abbr}")
            else:
                print(f"No predictions generated for {pitcher_name} vs {team_abbr}")
        
        # Handle individual matchup (batter vs pitcher)
        elif args.individual:
            batter_name, pitcher_name = param1, param2
            print(f"\n--- Enhanced Individual Matchup Analysis: {batter_name} vs {pitcher_name} ---")
            
            # If hitters file is provided, check if this batter is in the list
            if hitter_filtering_available and hitters_list and clean_player_name(batter_name) not in [clean_player_name(h) for h in hitters_list]:
                print(f"Batter '{batter_name}' is not in the provided hitters list. Skipping analysis.")
                return 1
            
            prediction = analyze_individual_matchup(
                batter_name, pitcher_name,
                master_player_data, name_to_player_id_map, daily_game_data,
                rosters_data, historical_data, league_avg_stats, metric_ranges
            )
            
            if prediction and prediction.get('score', 0) > 0:
                print(format_detailed_matchup_report(prediction))
                
                # Create single-prediction enhanced CSV
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = f"individual_enhanced_{batter_name.replace(' ', '_')}_vs_{pitcher_name.replace(' ', '_')}_{timestamp}.csv"
                create_predictions_csv_enhanced([prediction], csv_filename)
            else:
                print(f"No prediction generated for {batter_name} vs {pitcher_name}")
        
        # Default to team analysis
        else:
            print(f"Mode not specified. Assuming enhanced pitcher vs team analysis: {param1} vs {param2}")
            
            predictions = process_pitcher_vs_team(
                param1, param2,
                master_player_data, name_to_player_id_map, daily_game_data,
                rosters_data, historical_data, league_avg_stats, metric_ranges
            )
            
            if predictions:
                # Apply specific hitter filtering if provided
                if hitter_filtering_available and hitters_list:
                    filtered_by_hitters = filter_predictions_by_hitters(predictions, hitters_list)
                    print(f"Filtered to {len(filtered_by_hitters)} of {len(predictions)} hitters based on hitters file.")
                    predictions = filtered_by_hitters
                
                # Only proceed if we have predictions after hitter filtering
                if predictions:
                    # Apply any additional filters
                    if filter_criteria:
                        filtered_predictions = filter_predictions(predictions, filter_criteria)
                        filter_desc = ", ".join([f"{k}={v}" for k, v in filter_criteria.items()])
                        print(f"Applied filters ({filter_desc}): {len(filtered_predictions)} of {len(predictions)} predictions match.")
                        predictions = filtered_predictions
                    
                    # Only proceed if we have predictions after all filtering
                    if predictions:
                        # Sort predictions according to specified criteria
                        sorted_predictions = sort_predictions(predictions, sort_by=args.sort, ascending=args.ascending)
                        sort_desc = get_sort_description(args.sort)
                        order_desc = "ascending" if args.ascending else "descending"
                        
                        print(f"\n=== Enhanced Predictions: {param1} vs {param2} (Sorted by {sort_desc}, {order_desc}) ===")
                        
                        display_limit = None if args.all else args.limit
                        print_top_predictions(sorted_predictions, limit=display_limit, detailed=args.detailed)
                        
                        # Create enhanced CSV output
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        csv_filename = f"analysis_enhanced_{param1.replace(' ', '_')}_vs_{param2}_{timestamp}.csv"
                        create_predictions_csv_enhanced(sorted_predictions, csv_filename)
                    else:
                        print(f"No predictions match the filter criteria for {param1} vs {param2}")
                else:
                    print(f"No predictions match the specified hitters for {param1} vs {param2}")
            else:
                print(f"No predictions generated for {param1} vs {param2}")
    except Exception as e:
        print(f"ERROR during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    print("DEBUG: Script executing as main")
    try:
        exit_code = main()
        print(f"DEBUG: Exiting with code {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        print(f"DEBUG: Uncaught exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)