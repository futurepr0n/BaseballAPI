#!/usr/bin/env python3
"""
PORTED FROM PINHEAD-CLAUDE: Direct port of working functions
These functions have been proven to work reliably in the Pinhead-Claude system.
"""

import numpy as np
import pandas as pd
from utils import clean_player_name, match_player_name_to_roster
import logging

logger = logging.getLogger(__name__)

def get_last_n_games_performance_pitcher_ported(pitcher_full_name_resolved, daily_data, roster_data_list, n_games=7):
    """
    PORTED FROM PINHEAD-CLAUDE: Get the performance data for a pitcher's last N games.
    Enhanced with multiple name matching strategies and comprehensive logging.
    """
    logger.info(f"🎯 ENHANCED PITCHER LOOKUP: '{pitcher_full_name_resolved}'")
    logger.info(f"📊 Available data: {len(daily_data)} daily dates, {len(roster_data_list)} roster entries")
    
    # ENHANCED: Find pitcher's name with multiple matching strategies
    daily_pitcher_json_name = None
    matched_roster_entry = None
    
    # Strategy 1: Exact fullName matching
    for p_info_roster in roster_data_list:
        names_to_check = [
            p_info_roster.get('fullName'),
            p_info_roster.get('fullName_cleaned'),
            p_info_roster.get('fullName_resolved')
        ]
        
        for name_variant in names_to_check:
            if name_variant == pitcher_full_name_resolved:
                matched_roster_entry = p_info_roster
                daily_pitcher_json_name = p_info_roster.get('name')
                logger.info(f"✅ EXACT MATCH: '{pitcher_full_name_resolved}' → roster name: '{daily_pitcher_json_name}'")
                break
        if matched_roster_entry:
            break
    
    # Strategy 2: Case-insensitive matching
    if not daily_pitcher_json_name:
        pitcher_name_lower = pitcher_full_name_resolved.lower()
        for p_info_roster in roster_data_list:
            names_to_check = [
                p_info_roster.get('fullName', '').lower(),
                p_info_roster.get('fullName_cleaned', '').lower(),
                p_info_roster.get('fullName_resolved', '').lower()
            ]
            
            for name_variant in names_to_check:
                if name_variant == pitcher_name_lower:
                    matched_roster_entry = p_info_roster
                    daily_pitcher_json_name = p_info_roster.get('name')
                    logger.info(f"✅ CASE-INSENSITIVE MATCH: '{pitcher_full_name_resolved}' → roster name: '{daily_pitcher_json_name}'")
                    break
            if matched_roster_entry:
                break
    
    # Strategy 3: Fuzzy matching with difflib
    if not daily_pitcher_json_name:
        from difflib import get_close_matches
        
        all_roster_names = []
        name_to_roster_map = {}
        
        for p_info_roster in roster_data_list:
            for field in ['fullName', 'fullName_cleaned', 'fullName_resolved']:
                name_val = p_info_roster.get(field)
                if name_val:
                    all_roster_names.append(name_val)
                    name_to_roster_map[name_val] = p_info_roster
        
        fuzzy_matches = get_close_matches(pitcher_full_name_resolved, all_roster_names, n=1, cutoff=0.8)
        if fuzzy_matches:
            matched_name = fuzzy_matches[0]
            matched_roster_entry = name_to_roster_map[matched_name]
            daily_pitcher_json_name = matched_roster_entry.get('name')
            logger.info(f"🔍 FUZZY MATCH: '{pitcher_full_name_resolved}' → '{matched_name}' → roster name: '{daily_pitcher_json_name}'")
    
    # Strategy 4: Partial name matching (last resort)
    if not daily_pitcher_json_name:
        input_parts = pitcher_full_name_resolved.lower().split()
        for p_info_roster in roster_data_list:
            for field in ['fullName', 'fullName_cleaned', 'fullName_resolved']:
                roster_name = p_info_roster.get(field, '').lower()
                if roster_name:
                    roster_parts = roster_name.split()
                    # Check if all input parts are found in roster name
                    if all(any(input_part in roster_part for roster_part in roster_parts) for input_part in input_parts):
                        matched_roster_entry = p_info_roster
                        daily_pitcher_json_name = p_info_roster.get('name')
                        logger.info(f"🔍 PARTIAL MATCH: '{pitcher_full_name_resolved}' → '{p_info_roster.get(field)}' → roster name: '{daily_pitcher_json_name}'")
                        break
            if matched_roster_entry:
                break
    
    # If not found via roster match, search directly in daily data with enhanced matching
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
        logger.warning(f"❌ ENHANCED: Could not find pitcher '{pitcher_full_name_resolved}' using any matching strategy")
        logger.info(f"📋 Available roster pitchers: {[p.get('fullName', 'Unknown') for p in roster_data_list if p.get('type') == 'pitcher'][:10]}")
        return [], []
    
    logger.info(f"✅ ENHANCED: Found pitcher in daily data as: '{daily_pitcher_json_name}' (team: {matched_roster_entry.get('team', 'Unknown') if matched_roster_entry else 'Unknown'})")
    
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
            except (ValueError, TypeError) as e:
                pass
    
    last_n_games_data = games_performance_chrono[-n_games:]
    logger.info(f"✅ ENHANCED: Returning {len(last_n_games_data)} recent pitcher games")
    
    # Log sample of games found for debugging
    if last_n_games_data:
        sample_game = last_n_games_data[-1]  # Most recent
        logger.info(f"📈 Sample game: Date={sample_game.get('date')}, IP={sample_game.get('IP')}, ERA={sample_game.get('ERA')}, H={sample_game.get('H')}")
    
    # Return in reverse chronological order (most recent first)
    return last_n_games_data[::-1], []

def calculate_recent_trends_pitcher_ported(games_performance):
    """
    PORTED FROM PINHEAD-CLAUDE: Calculate performance trends from a pitcher's recent games.
    Enhanced with comprehensive logging and fallback handling.
    """
    if not games_performance:
        logger.warning("🎯 ENHANCED: No pitcher games to analyze - returning stable")
        return {'trend_direction': 'stable', 'trend_magnitude': 0.0}
    
    num_games = len(games_performance)
    logger.info(f"🎯 ENHANCED: Calculating pitcher trends for {num_games} games")
    
    # Log game details for debugging
    for i, game in enumerate(games_performance):
        logger.debug(f"  Game {i+1}: Date={game.get('date')}, IP={game.get('IP')}, ERA={game.get('ERA')}, H={game.get('H')}")
    
    # Calculate trends (first half vs second half) - EXACT PINHEAD-CLAUDE LOGIC
    recent_stats = {}
    
    if num_games >= 2:
        mid_point = num_games // 2
        # NOTE: games_performance comes in reverse chronological order (most recent first)
        recent_half_games = games_performance[:mid_point]  # Most recent games (first half)
        earlier_half_games = games_performance[mid_point:]  # Earlier games (second half)
        
        if recent_half_games and earlier_half_games:
            # ERA trend - EXACT PINHEAD-CLAUDE CALCULATION
            recent_era_list = [g['ERA'] for g in recent_half_games if g['IP'] > 0]
            early_era_list = [g['ERA'] for g in earlier_half_games if g['IP'] > 0]
            
            if recent_era_list and early_era_list:
                recent_era = np.mean(recent_era_list)
                early_era = np.mean(early_era_list)
                
                if pd.notna(recent_era) and pd.notna(early_era):
                    # ENHANCED TREND LOGIC with stability threshold
                    era_diff = abs(recent_era - early_era)
                    if era_diff < 0.25:  # Small difference = stable
                        trend_direction = 'stable'
                    elif recent_era < early_era:  # Recent ERA lower (better)
                        trend_direction = 'improving'
                    else:  # Recent ERA higher (worse)
                        trend_direction = 'declining'
                    recent_stats.update({
                        'trend_metric': 'ERA',
                        'trend_recent_val': round(recent_era, 3),
                        'trend_early_val': round(early_era, 3),
                        'trend_direction': trend_direction,
                        'trend_magnitude': abs(recent_era - early_era)
                    })
                    logger.info(f"🎯 ENHANCED PITCHER TREND: {trend_direction} (Early ERA: {early_era:.3f} → Recent ERA: {recent_era:.3f}, Magnitude: {abs(recent_era - early_era):.3f})")
    
    if 'trend_direction' not in recent_stats:
        recent_stats['trend_direction'] = 'stable'
        logger.info(f"🎯 DEFAULT TREND: Insufficient data for trend calculation - defaulting to stable")
    
    return recent_stats

def calculate_recent_trends_hitter_ported(games_performance):
    """
    PORTED FROM PINHEAD-CLAUDE: Calculate performance trends for a hitter.
    This implements the exact logic that works in Pinhead-Claude.
    """
    if not games_performance or len(games_performance) < 2:
        return {
            'trend_direction': 'stable',
            'trend_magnitude': 0.0,
            'avg_avg': 0.0
        }
    
    num_games = len(games_performance)
    logger.info(f"🎯 PORTED: Calculating hitter trends for {num_games} games")
    
    # Calculate overall average
    total_ab = sum(game.get('AB', 0) for game in games_performance)
    total_hits = sum(game.get('H', 0) for game in games_performance)
    total_hrs = sum(game.get('HR', 0) for game in games_performance)
    
    avg_avg = total_hits / total_ab if total_ab > 0 else 0.0
    
    # Calculate trend (first half vs second half) - EXACT PINHEAD-CLAUDE LOGIC
    if num_games >= 4:
        mid_point = num_games // 2
        recent_half = games_performance[:mid_point]  # More recent games
        early_half = games_performance[mid_point:]   # Earlier games
        
        # Calculate HR rate for each half
        recent_hrs = sum(game.get('HR', 0) for game in recent_half)
        recent_ab = sum(game.get('AB', 0) for game in recent_half)
        recent_hr_rate = recent_hrs / recent_ab if recent_ab > 0 else 0
        
        early_hrs = sum(game.get('HR', 0) for game in early_half)
        early_ab = sum(game.get('AB', 0) for game in early_half)
        early_hr_rate = early_hrs / early_ab if early_ab > 0 else 0
        
        # EXACT PINHEAD-CLAUDE TREND LOGIC
        if recent_hr_rate > early_hr_rate:
            trend_direction = 'improving'
        elif recent_hr_rate < early_hr_rate:
            trend_direction = 'declining'
        else:
            trend_direction = 'stable'
        
        trend_magnitude = abs(recent_hr_rate - early_hr_rate)
        
        logger.info(f"🎯 PORTED HITTER TREND: {trend_direction} (Early: {early_hr_rate:.3f}, Recent: {recent_hr_rate:.3f})")
        
        return {
            'trend_direction': trend_direction,
            'trend_magnitude': trend_magnitude,
            'avg_avg': avg_avg,
            'recent_hr_rate': recent_hr_rate,
            'early_hr_rate': early_hr_rate
        }
    
    return {
        'trend_direction': 'stable',
        'trend_magnitude': 0.0,
        'avg_avg': avg_avg
    }