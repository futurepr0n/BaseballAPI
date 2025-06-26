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
    This is the exact function that works reliably in Pinhead-Claude.
    """
    logger.info(f"🎯 PORTED PITCHER LOOKUP: {pitcher_full_name_resolved}")
    
    # Find pitcher's name as used in daily data
    daily_pitcher_json_name = None
    for p_info_roster in roster_data_list:
        if p_info_roster.get('fullName') == pitcher_full_name_resolved:
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
        logger.warning(f"⚠️ PORTED: Could not find pitcher {pitcher_full_name_resolved} in daily data")
        return [], []
    
    logger.info(f"✅ PORTED: Found pitcher in daily data as: {daily_pitcher_json_name}")
    
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
    logger.info(f"✅ PORTED: Returning {len(last_n_games_data)} recent pitcher games")
    # Return in reverse chronological order (most recent first)
    return last_n_games_data[::-1], []

def calculate_recent_trends_pitcher_ported(games_performance):
    """
    PORTED FROM PINHEAD-CLAUDE: Calculate performance trends from a pitcher's recent games.
    This is the exact function that works reliably in Pinhead-Claude.
    """
    if not games_performance:
        logger.warning("🎯 PORTED: No pitcher games to analyze")
        return {}
    
    num_games = len(games_performance)
    logger.info(f"🎯 PORTED: Calculating pitcher trends for {num_games} games")
    
    # Calculate trends (first half vs second half) - EXACT PINHEAD-CLAUDE LOGIC
    recent_stats = {}
    
    if num_games >= 2:
        mid_point = num_games // 2
        recent_half_games = games_performance[:mid_point]  # More recent games
        earlier_half_games = games_performance[mid_point:]  # Earlier games
        
        if recent_half_games and earlier_half_games:
            # ERA trend - EXACT PINHEAD-CLAUDE CALCULATION
            recent_era_list = [g['ERA'] for g in recent_half_games if g['IP'] > 0]
            early_era_list = [g['ERA'] for g in earlier_half_games if g['IP'] > 0]
            
            if recent_era_list and early_era_list:
                recent_era = np.mean(recent_era_list)
                early_era = np.mean(early_era_list)
                
                if pd.notna(recent_era) and pd.notna(early_era):
                    # EXACT PINHEAD-CLAUDE TREND LOGIC
                    trend_direction = 'improving' if recent_era < early_era else 'declining' if recent_era > early_era else 'stable'
                    recent_stats.update({
                        'trend_metric': 'ERA',
                        'trend_recent_val': round(recent_era, 3),
                        'trend_early_val': round(early_era, 3),
                        'trend_direction': trend_direction,
                        'trend_magnitude': abs(recent_era - early_era)
                    })
                    logger.info(f"🎯 PORTED PITCHER TREND: {trend_direction} ({early_era:.3f} -> {recent_era:.3f})")
    
    if 'trend_direction' not in recent_stats:
        recent_stats['trend_direction'] = 'stable'
    
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