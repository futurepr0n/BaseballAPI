import numpy as np
import pandas as pd
from collections import defaultdict
from utils import (
    normalize_calculated, 
    adjust_stat_with_confidence,
    get_approximated_pa
)

# Enhanced configuration for missing data handling
ENHANCED_WEIGHTS = {
    'batter_vs_pitch_slg': 1.5, 'batter_vs_pitch_hr': 2.0, 'batter_vs_pitch_hard_hit': 1.0,
    'batter_batted_ball_fb': 0.8, 'batter_batted_ball_pull_air': 1.2,
    'pitcher_vulnerability_slg': 1.2, 'pitcher_vulnerability_hr': 1.8, 'pitcher_vulnerability_hard_hit': 0.8,
    'pitcher_run_value_penalty': 1.0,
    'batter_overall_brl_percent': 2.5, 'batter_overall_hard_hit': 1.2, 'batter_overall_iso': 1.5,
    'pitcher_overall_brl_percent_allowed': 2.0, 'pitcher_overall_hard_hit_allowed': 1.0,
    'historical_trend_bonus': 0.7, 'historical_consistency_bonus': 0.3,
    'recent_performance_bonus': 1.5,
    'ev_matchup_bonus': 1.0,
    'due_for_hr_factor': 0.5, 'due_for_hr_hits_factor': 0.3,
    'heating_up_contact_factor': 0.4, 'cold_batter_factor': 0.4,
    'hitter_pitch_rv_advantage': 0.8, 'hitter_pitch_k_avoidance': 0.4,
    'pitcher_pitch_k_ability': 0.4,
    'trend_2025_vs_2024_bonus': 0.8,
    # New weights for fallback scenarios
    'league_average_bonus': 0.3,
    'team_pitching_bonus': 0.5,
    'position_type_bonus': 0.4
}

# Dynamic component weights - adjust based on data availability
DEFAULT_COMPONENT_WEIGHTS = {
    'arsenal_matchup': 0.40,
    'batter_overall': 0.15,
    'pitcher_overall': 0.10,
    'historical_yoy_csv': 0.05,
    'recent_daily_games': 0.10,
    'contextual': 0.20
}

# Fallback component weights when pitcher arsenal data is missing
FALLBACK_COMPONENT_WEIGHTS = {
    'arsenal_matchup': 0.25,  # Reduced since using league averages
    'batter_overall': 0.25,   # Increased to compensate
    'pitcher_overall': 0.15,  # Increased
    'historical_yoy_csv': 0.10, # Increased
    'recent_daily_games': 0.15,  # Increased
    'contextual': 0.20        # Unchanged
}

# League average pitch type distribution (when pitcher data unavailable)
LEAGUE_AVERAGE_PITCH_DISTRIBUTION = {
    'FF': {'usage': 35.5, 'name': 'Four-Seam Fastball'},
    'SI': {'usage': 18.2, 'name': 'Sinker'},
    'SL': {'usage': 15.8, 'name': 'Slider'},
    'CH': {'usage': 12.1, 'name': 'Changeup'},
    'CU': {'usage': 8.7, 'name': 'Curveball'},
    'FC': {'usage': 6.2, 'name': 'Cutter'},
    'KC': {'usage': 2.8, 'name': 'Knuckle Curve'},
    'FS': {'usage': 0.7, 'name': 'Splitter'}
}

# Default league average performance vs each pitch type
LEAGUE_AVERAGE_PERFORMANCE_BY_PITCH = {
    'FF': {'ba': 0.265, 'slg': 0.425, 'woba': 0.335, 'hard_hit_percent': 38.5, 'k_percent': 22.8, 'run_value_per_100': 0.2},
    'SI': {'ba': 0.275, 'slg': 0.395, 'woba': 0.315, 'hard_hit_percent': 35.2, 'k_percent': 18.5, 'run_value_per_100': -0.5},
    'SL': {'ba': 0.225, 'slg': 0.365, 'woba': 0.295, 'hard_hit_percent': 32.1, 'k_percent': 28.7, 'run_value_per_100': -1.2},
    'CH': {'ba': 0.235, 'slg': 0.375, 'woba': 0.305, 'hard_hit_percent': 30.8, 'k_percent': 26.3, 'run_value_per_100': -0.8},
    'CU': {'ba': 0.215, 'slg': 0.345, 'woba': 0.285, 'hard_hit_percent': 28.9, 'k_percent': 32.1, 'run_value_per_100': -1.8},
    'FC': {'ba': 0.245, 'slg': 0.385, 'woba': 0.315, 'hard_hit_percent': 34.2, 'k_percent': 24.5, 'run_value_per_100': -0.3},
    'KC': {'ba': 0.205, 'slg': 0.335, 'woba': 0.275, 'hard_hit_percent': 27.5, 'k_percent': 35.2, 'run_value_per_100': -2.1},
    'FS': {'ba': 0.220, 'slg': 0.355, 'woba': 0.290, 'hard_hit_percent': 29.8, 'k_percent': 30.5, 'run_value_per_100': -1.5}
}

def calculate_league_averages_by_pitch_type(master_player_data, min_pa_threshold=50):
    """
    Calculate real-time league averages for each pitch type from actual data.
    Fallback to defaults if insufficient data.
    """
    print("Calculating real-time league averages by pitch type...")
    
    pitch_type_accumulator = defaultdict(lambda: defaultdict(list))
    
    for pid, pdata in master_player_data.items():
        # Collect hitter performance vs pitch types
        hitter_arsenal = pdata.get('hitter_pitch_arsenal_stats', {})
        if isinstance(hitter_arsenal, dict):
            for pitch_type, stats in hitter_arsenal.items():
                if isinstance(stats, dict):
                    for metric in ['ba', 'slg', 'woba', 'hard_hit_percent', 'k_percent', 'run_value_per_100']:
                        value = stats.get(metric)
                        if pd.notna(value) and value is not None:
                            # Normalize percentage values
                            if metric in ['hard_hit_percent', 'k_percent']:
                                value = value / 100.0 if value > 1 else value
                            pitch_type_accumulator[pitch_type][metric].append(value)
        
        # Collect pitcher performance with pitch types
        pitcher_arsenal = pdata.get('pitcher_pitch_arsenal_stats', {})
        if isinstance(pitcher_arsenal, dict):
            for pitch_type, stats in pitcher_arsenal.items():
                if isinstance(stats, dict):
                    for metric in ['ba', 'slg', 'woba', 'hard_hit_percent', 'k_percent', 'run_value_per_100']:
                        value = stats.get(metric)
                        if pd.notna(value) and value is not None:
                            if metric in ['hard_hit_percent', 'k_percent']:
                                value = value / 100.0 if value > 1 else value
                            pitch_type_accumulator[pitch_type][metric].append(value)
    
    # Calculate averages with fallback to defaults
    league_avg_by_pitch = {}
    for pitch_type in LEAGUE_AVERAGE_PITCH_DISTRIBUTION.keys():
        league_avg_by_pitch[pitch_type] = {}
        
        for metric in ['ba', 'slg', 'woba', 'hard_hit_percent', 'k_percent', 'run_value_per_100']:
            values = pitch_type_accumulator[pitch_type][metric]
            
            if len(values) >= min_pa_threshold:
                # Use actual league data
                league_avg_by_pitch[pitch_type][metric] = np.mean(values)
            else:
                # Fallback to defaults
                default_val = LEAGUE_AVERAGE_PERFORMANCE_BY_PITCH.get(pitch_type, {}).get(metric, 0.250)
                league_avg_by_pitch[pitch_type][metric] = default_val
                
        # Add usage from defaults (could be calculated from data in future)
        league_avg_by_pitch[pitch_type]['usage'] = LEAGUE_AVERAGE_PITCH_DISTRIBUTION[pitch_type]['usage']
        league_avg_by_pitch[pitch_type]['name'] = LEAGUE_AVERAGE_PITCH_DISTRIBUTION[pitch_type]['name']
    
    print(f"Calculated league averages for {len(league_avg_by_pitch)} pitch types")
    return league_avg_by_pitch

def get_team_pitching_profile(team_abbr, master_player_data):
    """
    Calculate team-level pitching tendencies when individual pitcher data is missing.
    """
    team_pitchers = []
    team_metrics = defaultdict(list)
    
    for pid, pdata in master_player_data.items():
        roster_info = pdata.get('roster_info', {})
        if (roster_info.get('type') == 'pitcher' and 
            roster_info.get('team', '').upper() == team_abbr.upper()):
            
            # Collect overall pitcher stats
            pitcher_ev_stats = pdata.get('pitcher_overall_ev_stats', {})
            if isinstance(pitcher_ev_stats, dict):
                for metric in ['brl_percent', 'hard_hit_percent', 'slg_percent']:
                    value = pitcher_ev_stats.get(metric)
                    if pd.notna(value):
                        team_metrics[metric].append(value)
            
            # Collect arsenal stats if available
            pitcher_arsenal = pdata.get('pitcher_pitch_arsenal_stats', {})
            if isinstance(pitcher_arsenal, dict):
                team_pitchers.append(pid)
    
    # Calculate team averages
    team_profile = {}
    for metric, values in team_metrics.items():
        if values:
            team_profile[f'team_avg_{metric}'] = np.mean(values)
    
    team_profile['num_pitchers_with_data'] = len(team_pitchers)
    return team_profile

def get_position_based_profile(pitcher_roster_info, league_avg_stats):
    """
    Provide different baseline expectations for starters vs relievers vs closers.
    """
    # This would ideally use roster position data or inning-based analysis
    # For now, provide differentiated baselines
    
    position_type = 'starter'  # Default assumption
    
    # Starters typically:
    # - Face batters multiple times
    # - Have more diverse arsenals
    # - Show more fatigue effects
    starter_modifiers = {
        'slg_modifier': 1.05,      # Slightly higher SLG allowed (fatigue)
        'k_rate_modifier': 0.95,   # Slightly lower K rate
        'usage_diversity': 1.2     # More diverse pitch mix
    }
    
    # Relievers typically:
    # - Face batters once
    # - Have more focused arsenals
    # - Throw harder
    reliever_modifiers = {
        'slg_modifier': 0.95,      # Lower SLG allowed
        'k_rate_modifier': 1.10,   # Higher K rate
        'usage_diversity': 0.8     # More focused pitch mix
    }
    
    modifiers = starter_modifiers  # Default to starter
    
    return {
        'position_type': position_type,
        'modifiers': modifiers,
        'confidence_penalty': 0.15  # Reduce confidence when using position-based estimates
    }

def enhanced_arsenal_matchup_with_fallbacks(batter_id, pitcher_id, master_player_data, 
                                          league_avg_by_pitch_type, current_year=2025):
    """
    Enhanced arsenal analysis that gracefully handles missing pitcher data.
    Uses league averages, team profiles, and position-based estimates as fallbacks.
    """
    batter_data = master_player_data.get(str(batter_id))
    pitcher_data = master_player_data.get(str(pitcher_id))
    
    if not batter_data:
        return {
            "error": "Batter data not found.",
            "confidence": 0.0,
            "data_source": "none",
            "pitch_matchups": [],
            "overall_summary_metrics": {}
        }
    
    if not pitcher_data:
        return {
            "error": "Pitcher data not found.",
            "confidence": 0.0,
            "data_source": "none", 
            "pitch_matchups": [],
            "overall_summary_metrics": {}
        }
    
    pitcher_roster_info = pitcher_data.get('roster_info', {})
    pitcher_team = pitcher_roster_info.get('team', 'UNK')
    
    # Try to get actual pitcher arsenal data
    pitcher_arsenal_stats = pitcher_data.get('pitcher_pitch_arsenal_stats', {})
    pitcher_usage_stats = pitcher_data.get('pitch_usage_stats', {})
    
    confidence_level = 1.0
    data_source = "full"
    arsenal_to_use = {}
    usage_to_use = {}
    
    # Determine data source and confidence level
    if pitcher_usage_stats and len(pitcher_usage_stats) >= 3:
        # Full pitcher data available
        arsenal_to_use = pitcher_arsenal_stats
        usage_to_use = pitcher_usage_stats
        confidence_level = 1.0
        data_source = "pitcher_specific"
        
    elif pitcher_usage_stats and len(pitcher_usage_stats) >= 1:
        # Partial pitcher data - blend with league averages
        arsenal_to_use = pitcher_arsenal_stats
        usage_to_use = pitcher_usage_stats
        confidence_level = 0.7
        data_source = "pitcher_partial"
        
        # Fill in missing pitch types with league averages
        total_known_usage = sum(usage_to_use.values())
        remaining_usage = 100 - total_known_usage
        
        if remaining_usage > 10:  # Significant missing usage
            # Add league average pitch types to fill the gap
            for pitch_type, league_data in league_avg_by_pitch_type.items():
                if pitch_type not in usage_to_use:
                    # Scale league usage by remaining percentage
                    scaled_usage = (league_data['usage'] / 100) * remaining_usage
                    usage_to_use[pitch_type] = scaled_usage
                    arsenal_to_use[pitch_type] = league_data.copy()
                    
    else:
        # No pitcher-specific data - use fallback strategies
        confidence_level = 0.4
        
        # Try team-based profile first
        team_profile = get_team_pitching_profile(pitcher_team, master_player_data)
        
        if team_profile.get('num_pitchers_with_data', 0) >= 3:
            # Use team-based estimates
            data_source = "team_based"
            confidence_level = 0.5
            
            # Create blended arsenal using team tendencies and league averages
            for pitch_type, league_data in league_avg_by_pitch_type.items():
                usage_to_use[pitch_type] = league_data['usage']
                
                # Blend team and league averages
                team_modifier = 1.0
                if f'team_avg_slg_percent' in team_profile:
                    team_modifier = team_profile['team_avg_slg_percent'] / 0.420  # Normalize to league avg
                
                arsenal_stats = league_data.copy()
                arsenal_stats['slg'] = league_data['slg'] * team_modifier
                arsenal_stats['woba'] = league_data['woba'] * (team_modifier * 0.8)  # Dampen effect
                arsenal_to_use[pitch_type] = arsenal_stats
                
        else:
            # Use pure league averages with position-based adjustments
            data_source = "league_average"
            position_profile = get_position_based_profile(pitcher_roster_info, {})
            confidence_level = 0.3 - position_profile.get('confidence_penalty', 0.1)
            
            for pitch_type, league_data in league_avg_by_pitch_type.items():
                usage_to_use[pitch_type] = league_data['usage']
                
                # Apply position-based modifiers
                arsenal_stats = league_data.copy()
                modifiers = position_profile.get('modifiers', {})
                
                arsenal_stats['slg'] = league_data['slg'] * modifiers.get('slg_modifier', 1.0)
                arsenal_stats['k_percent'] = league_data['k_percent'] * modifiers.get('k_rate_modifier', 1.0)
                arsenal_to_use[pitch_type] = arsenal_stats
    
    # Proceed with matchup analysis using determined arsenal
    matchup_details = []
    weighted_metrics = defaultdict(lambda: {'sum_weighted_values': 0, 'sum_weights': 0})
    
    metrics_to_analyze = ['ba', 'slg', 'woba', 'hard_hit_percent', 'k_percent', 'run_value_per_100']
    
    for pitch_type, usage_percent in usage_to_use.items():
        if usage_percent < 3:  # Skip very low usage pitches
            continue
            
        usage_weight = usage_percent / 100.0
        
        # Get batter performance vs this pitch type
        batter_arsenal = batter_data.get('hitter_pitch_arsenal_stats', {})
        batter_vs_pitch = batter_arsenal.get(pitch_type, {})
        
        # Get pitcher performance with this pitch type
        pitcher_vs_pitch = arsenal_to_use.get(pitch_type, {})
        
        pitch_matchup = {
            'pitch_type': pitch_type,
            'pitch_name': pitcher_vs_pitch.get('name', pitch_type),
            'usage': usage_percent,
            'data_source': data_source,
            'confidence': confidence_level
        }
        
        current_year_stats = {}
        
        for metric in metrics_to_analyze:
            # Batter value (prefer actual data, fallback to league avg if missing)
            batter_value = batter_vs_pitch.get(metric)
            if not pd.notna(batter_value) or batter_value is None:
                batter_value = league_avg_by_pitch_type.get(pitch_type, {}).get(metric, 0.250)
            
            # Pitcher value (from our determined arsenal)
            pitcher_value = pitcher_vs_pitch.get(metric)
            if not pd.notna(pitcher_value) or pitcher_value is None:
                pitcher_value = league_avg_by_pitch_type.get(pitch_type, {}).get(metric, 0.250)
            
            # Normalize percentage values
            if metric in ['hard_hit_percent', 'k_percent']:
                if batter_value > 1:
                    batter_value /= 100.0
                if pitcher_value > 1:
                    pitcher_value /= 100.0
            
            current_year_stats[f'hitter_{metric}'] = batter_value
            current_year_stats[f'pitcher_{metric}'] = pitcher_value
            
            # Accumulate weighted averages
            if pd.notna(batter_value):
                weighted_metrics[f'hitter_avg_{metric}']['sum_weighted_values'] += batter_value * usage_weight
                weighted_metrics[f'hitter_avg_{metric}']['sum_weights'] += usage_weight
            
            if pd.notna(pitcher_value):
                weighted_metrics[f'pitcher_avg_{metric}']['sum_weighted_values'] += pitcher_value * usage_weight
                weighted_metrics[f'pitcher_avg_{metric}']['sum_weights'] += usage_weight
        
        pitch_matchup['current_year_stats'] = current_year_stats
        matchup_details.append(pitch_matchup)
    
    # Calculate overall weighted metrics
    overall_metrics = {}
    for metric_name, data_sums in weighted_metrics.items():
        if data_sums['sum_weights'] > 0:
            overall_metrics[metric_name] = data_sums['sum_weighted_values'] / data_sums['sum_weights']
        else:
            overall_metrics[metric_name] = None
    
    return {
        "pitch_matchups": matchup_details,
        "overall_summary_metrics": overall_metrics,
        "batter_id": batter_id,
        "pitcher_id": pitcher_id,
        "confidence": confidence_level,
        "data_source": data_source,
        "data_quality_info": {
            "pitcher_usage_pitches": len(usage_to_use),
            "pitcher_arsenal_pitches": len(arsenal_to_use),
            "fallback_strategy": data_source,
            "confidence_level": confidence_level
        }
    }

def enhanced_hr_score_with_missing_data_handling(batter_mlbam_id, pitcher_mlbam_id, master_player_data, 
                                               historical_data, metric_ranges, league_avg_stats, 
                                               league_avg_by_pitch_type, recent_batter_stats=None):
    """
    Enhanced HR likelihood calculation that gracefully handles missing pitcher data.
    Automatically adjusts component weights and provides confidence indicators.
    """
    batter_data = master_player_data.get(str(batter_mlbam_id))
    pitcher_data = master_player_data.get(str(pitcher_mlbam_id))
    
    if not batter_data or not pitcher_data:
        return {'score': 0, 'reason': "Missing player master data", 'confidence': 0.0}
    
    batter_roster_info = batter_data.get('roster_info', {})
    pitcher_roster_info = pitcher_data.get('roster_info', {})
    
    batter_name = batter_roster_info.get('fullName_resolved', f"BatterID:{batter_mlbam_id}")
    pitcher_name = pitcher_roster_info.get('fullName_resolved', f"PitcherID:{pitcher_mlbam_id}")
    
    batter_hand = batter_roster_info.get('bats', 'R')
    pitcher_hand = pitcher_roster_info.get('ph', 'R')
    
    # Adjust for switch hitters
    if batter_hand == 'B':
        batter_hand = 'L' if pitcher_hand == 'R' else 'R'
    
    batter_stats_2025_agg = batter_data.get('stats_2025_aggregated', {})
    batter_pa_2025 = batter_stats_2025_agg.get('PA_approx', 0)
    
    
    # Enhanced arsenal analysis with fallbacks
    arsenal_analysis = enhanced_arsenal_matchup_with_fallbacks(
        batter_mlbam_id, pitcher_mlbam_id, master_player_data, league_avg_by_pitch_type
    )
    
    overall_confidence = arsenal_analysis.get('confidence', 0.3)
    data_source = arsenal_analysis.get('data_source', 'unknown')
    
    # Dynamically adjust component weights based on data availability
    if overall_confidence >= 0.8:
        component_weights = DEFAULT_COMPONENT_WEIGHTS
    else:
        component_weights = FALLBACK_COMPONENT_WEIGHTS.copy()
        
        # Further adjust based on confidence level
        confidence_factor = overall_confidence
        component_weights['arsenal_matchup'] *= confidence_factor
        
        # Redistribute weight to more reliable components
        weight_to_redistribute = DEFAULT_COMPONENT_WEIGHTS['arsenal_matchup'] - component_weights['arsenal_matchup']
        component_weights['batter_overall'] += weight_to_redistribute * 0.4
        component_weights['recent_daily_games'] += weight_to_redistribute * 0.3
        component_weights['contextual'] += weight_to_redistribute * 0.3
    
    # Calculate hitter and pitcher SLG for details
    hitter_slg = batter_stats_2025_agg.get('SLG', 0)
    if hitter_slg == 0:
        # Calculate from basic stats if not directly available
        h = batter_stats_2025_agg.get('H', 0)
        doubles = batter_stats_2025_agg.get('2B', 0)
        triples = batter_stats_2025_agg.get('3B', 0)
        hr = batter_stats_2025_agg.get('HR', 0)
        ab = batter_stats_2025_agg.get('AB', 0)
        if ab > 0:
            # Correct SLG calculation: singles + 2*2B + 3*3B + 4*HR
            singles = h - doubles - triples - hr
            total_bases = singles + (2 * doubles) + (3 * triples) + (4 * hr)
            hitter_slg = total_bases / ab
    
    # Get pitcher SLG against (if available from pitcher stats)
    pitcher_stats_2025 = pitcher_data.get('stats_2025_aggregated', {})
    
    
    pitcher_slg = pitcher_stats_2025.get('SLG_against', 0)
    if pitcher_slg == 0:
        pitcher_slg = pitcher_stats_2025.get('SLG', 0)  # Fallback to regular SLG
    
    details_dict = {
        'batter_pa_2025': batter_pa_2025,
        'hitter_slg': round(hitter_slg, 3),
        'pitcher_slg': round(pitcher_slg, 3),
        # Placeholders for weather data (filled by dashboard context)
        'weather_factor': 1.0,
        'wind_factor': 1.0,
        'data_source': data_source,
        'overall_confidence': overall_confidence,
        'component_weights_used': component_weights,
        'arsenal_analysis': arsenal_analysis
    }
    
    # 1. Arsenal matchup score (with enhanced fallback handling)
    arsenal_score = 0
    if "error" not in arsenal_analysis and arsenal_analysis.get('pitch_matchups'):
        hitter_weighted_slg = arsenal_analysis.get('overall_summary_metrics', {}).get('hitter_avg_slg')
        pitcher_weighted_slg = arsenal_analysis.get('overall_summary_metrics', {}).get('pitcher_avg_slg')
        
        if hitter_weighted_slg is not None and pitcher_weighted_slg is not None:
            norm_h_slg = normalize_calculated(hitter_weighted_slg, 'slg', metric_ranges, higher_is_better=True)
            norm_p_slg = normalize_calculated(pitcher_weighted_slg, 'slg', metric_ranges, higher_is_better=True)
            arsenal_score = (norm_h_slg * 0.6 + norm_p_slg * 0.4)
            
            # Apply confidence adjustment
            arsenal_score = arsenal_score * overall_confidence + (50 * (1 - overall_confidence))
        else:
            arsenal_score = 40  # Conservative estimate when metrics unavailable
    else:
        arsenal_score = 35  # Conservative estimate for errors
        details_dict['arsenal_error'] = arsenal_analysis.get("error", "Unknown error")
    
    # 2. Batter overall score (unchanged - always based on batter data)
    batter_overall_score = 0
    hitter_ev_stats = batter_data.get('hitter_overall_ev_stats', {})
    
    if isinstance(hitter_ev_stats, dict):
        # ISO is not directly in exit velocity stats - calculate from aggregated stats or CSV
        iso_from_csv = hitter_ev_stats.get('iso_percent')  # This field doesn't exist in current CSV
        if not pd.notna(iso_from_csv):
            # Calculate ISO from our aggregated stats or from SLG/AVG in CSV
            slg_from_csv = hitter_ev_stats.get('slg_percent')
            avg_from_csv = hitter_ev_stats.get('batting_avg')
            if pd.notna(slg_from_csv) and pd.notna(avg_from_csv):
                iso_from_csv = slg_from_csv - avg_from_csv
            else:
                # Use our calculated ISO from aggregated stats
                iso_from_csv = batter_stats_2025_agg.get('ISO', 0)
        
        iso_adj = adjust_stat_with_confidence(
            iso_from_csv,
            batter_pa_2025,
            'ISO',
            league_avg_stats,
            default_league_avg_override=league_avg_stats['ISO']
        )
        
        brl_raw = (hitter_ev_stats.get('brl_percent') / 100.0) if pd.notna(hitter_ev_stats.get('brl_percent')) else league_avg_stats['AVG_BRL_PERCENT']
        hh_raw = (hitter_ev_stats.get('hard_hit_percent') / 100.0) if pd.notna(hitter_ev_stats.get('hard_hit_percent')) else league_avg_stats['AVG_HARD_HIT_PERCENT']
        
        batter_overall_score += ENHANCED_WEIGHTS['batter_overall_iso'] * normalize_calculated(iso_adj, 'iso', metric_ranges)
        batter_overall_score += ENHANCED_WEIGHTS['batter_overall_brl_percent'] * normalize_calculated(brl_raw, 'brl_percent', metric_ranges)
        batter_overall_score += ENHANCED_WEIGHTS['batter_overall_hard_hit'] * normalize_calculated(hh_raw, 'hard_hit_percent', metric_ranges)
        
        details_dict.update({
            'batter_iso_adj': round(iso_adj if pd.notna(iso_adj) else 0, 3),
            'batter_brl': round(brl_raw, 3),
            'batter_hh': round(hh_raw, 3)
        })
    
    # 3. Pitcher overall score (with missing data handling)
    pitcher_overall_score = 0
    pitcher_ev_stats = pitcher_data.get('pitcher_overall_ev_stats', {})
    
    if isinstance(pitcher_ev_stats, dict) and pitcher_ev_stats:
        # Use actual pitcher data
        brl_allowed = (pitcher_ev_stats.get('brl_percent') / 100.0) if pd.notna(pitcher_ev_stats.get('brl_percent')) else league_avg_stats['AVG_BRL_PERCENT']
        hh_allowed = (pitcher_ev_stats.get('hard_hit_percent') / 100.0) if pd.notna(pitcher_ev_stats.get('hard_hit_percent')) else league_avg_stats['AVG_HARD_HIT_PERCENT']
        
        pitcher_overall_score += ENHANCED_WEIGHTS['pitcher_overall_brl_percent_allowed'] * normalize_calculated(brl_allowed, 'brl_percent', metric_ranges, higher_is_better=True)
        pitcher_overall_score += ENHANCED_WEIGHTS['pitcher_overall_hard_hit_allowed'] * normalize_calculated(hh_allowed, 'hard_hit_percent', metric_ranges, higher_is_better=True)
        
        details_dict['pitcher_data_source'] = 'specific'
    else:
        # Use league averages or team-based estimates
        pitcher_team = pitcher_roster_info.get('team', 'UNK')
        team_profile = get_team_pitching_profile(pitcher_team, master_player_data)
        
        if team_profile.get('num_pitchers_with_data', 0) >= 2:
            # Use team averages
            brl_allowed = team_profile.get('team_avg_brl_percent', league_avg_stats['AVG_BRL_PERCENT'] * 100) / 100.0
            hh_allowed = team_profile.get('team_avg_hard_hit_percent', league_avg_stats['AVG_HARD_HIT_PERCENT'] * 100) / 100.0
            details_dict['pitcher_data_source'] = 'team_based'
        else:
            # Use league averages
            brl_allowed = league_avg_stats['AVG_BRL_PERCENT']
            hh_allowed = league_avg_stats['AVG_HARD_HIT_PERCENT']
            details_dict['pitcher_data_source'] = 'league_average'
        
        pitcher_overall_score += ENHANCED_WEIGHTS['pitcher_overall_brl_percent_allowed'] * normalize_calculated(brl_allowed, 'brl_percent', metric_ranges, higher_is_better=True)
        pitcher_overall_score += ENHANCED_WEIGHTS['pitcher_overall_hard_hit_allowed'] * normalize_calculated(hh_allowed, 'hard_hit_percent', metric_ranges, higher_is_better=True)
        
        # Apply penalty for using estimates
        pitcher_overall_score *= 0.8
    
    details_dict.update({
        'pitcher_brl_allowed': round(brl_allowed if 'brl_allowed' in locals() else 0, 3),
        'pitcher_hh_allowed': round(hh_allowed if 'hh_allowed' in locals() else 0, 3)
    })
    
    # 4. Historical trends (unchanged)
    historical_trends = analyze_historical_trends_general(
        str(batter_mlbam_id), historical_data, 'hitter_arsenal', ['slg', 'woba']
    )
    historical_score = calculate_general_historical_bonus(historical_trends)
    
    # 5. Recent performance (enhanced with proper data structure)
    recent_score = calculate_recent_performance_bonus(recent_batter_stats, 'hitter')
    
    # Create proper recent games data structure for sorting compatibility
    recent_N_games_raw_data = {}
    if recent_batter_stats:
        recent_N_games_raw_data = {
            'games_list': [],  # Would be populated with actual daily games if available
            'trends_summary_obj': {
                'total_games': recent_batter_stats.get('total_games', 0),
                'avg_avg': recent_batter_stats.get('avg_avg', 0),
                'hr_rate': recent_batter_stats.get('hr_per_pa', 0),
                'hr_per_pa': recent_batter_stats.get('hr_per_pa', 0),
                'obp_calc': recent_batter_stats.get('hit_rate', 0),  # Approximation
                'trend_direction': recent_batter_stats.get('trend_direction', 'stable'),
                'trend_magnitude': recent_batter_stats.get('trend_magnitude', 0.0),
                'trend_early_val': recent_batter_stats.get('trend_early_val', 0),
                'trend_recent_val': recent_batter_stats.get('trend_recent_val', 0),
                'trend_metric': 'HR_per_PA'
            },
            'at_bats': []  # Would be populated with detailed at-bat data if available
        }
    
    # 6. Contextual factors (enhanced with missing data awareness)
    contextual_score = 0
    
    # EV matchup (handle missing pitcher data)
    if isinstance(hitter_ev_stats, dict) and isinstance(pitcher_ev_stats, dict) and pitcher_ev_stats:
        h_hh = hitter_ev_stats.get('hard_hit_percent', league_avg_stats['AVG_HARD_HIT_PERCENT'] * 100)
        p_hh = pitcher_ev_stats.get('hard_hit_percent', league_avg_stats['AVG_HARD_HIT_PERCENT'] * 100)
    else:
        h_hh = hitter_ev_stats.get('hard_hit_percent', league_avg_stats['AVG_HARD_HIT_PERCENT'] * 100) if isinstance(hitter_ev_stats, dict) else league_avg_stats['AVG_HARD_HIT_PERCENT'] * 100
        p_hh = league_avg_stats['AVG_HARD_HIT_PERCENT'] * 100  # Use league average for pitcher
    
    norm_h_hh = normalize_calculated(h_hh / 100.0, 'hard_hit_percent', metric_ranges, higher_is_better=True)
    norm_p_hh = normalize_calculated(p_hh / 100.0, 'hard_hit_percent', metric_ranges, higher_is_better=True)
    ev_matchup_score = (norm_h_hh * 0.6 + norm_p_hh * 0.4) - 50
    
    contextual_score += ENHANCED_WEIGHTS['ev_matchup_bonus'] * (ev_matchup_score / 50 if ev_matchup_score != 0 else 0)
    
    # Store EV matchup score in details
    details_dict['ev_matchup_score'] = round(ev_matchup_score, 1)
    
    # Due for HR calculations - AB-based
    due_for_hr_ab_score = 0
    stats_2024_hitter = batter_data.get('stats_2024', {})
    hr_2024_val, ab_2024_val = stats_2024_hitter.get('HR', 0), stats_2024_hitter.get('AB', 0)
    hr_2025_agg_val, ab_2025_agg_val = batter_stats_2025_agg.get('HR', 0), batter_stats_2025_agg.get('AB', 0)
    
    # Calculate expected HR per AB
    expected_hr_per_ab_val = 0
    if hr_2024_val > 0 and ab_2024_val >= 50:
        expected_hr_per_ab_val = hr_2024_val / ab_2024_val
    elif hr_2025_agg_val > 0 and ab_2025_agg_val >= 30:
        expected_hr_per_ab_val = hr_2025_agg_val / ab_2025_agg_val
    else:
        expected_hr_per_ab_val = 1 / 45.0  # League average
    
    if expected_hr_per_ab_val > 0:
        ab_needed_for_hr_val = 1 / expected_hr_per_ab_val
        current_ab_since_hr_val = batter_stats_2025_agg.get('current_AB_since_last_HR', 0)
        
        details_dict.update({
            'ab_since_last_hr': current_ab_since_hr_val,
            'expected_ab_per_hr': round(ab_needed_for_hr_val, 1)
        })
        
        if current_ab_since_hr_val > ab_needed_for_hr_val * 1.25:
            due_for_hr_ab_score = min((current_ab_since_hr_val / ab_needed_for_hr_val - 1.25) * 20, 25)
    
    contextual_score += ENHANCED_WEIGHTS['due_for_hr_factor'] * (due_for_hr_ab_score / 25 if due_for_hr_ab_score != 0 else 0)
    
    # Due for HR calculations - Hits-based
    due_for_hr_hits_score = 0
    current_h_since_hr_val = batter_stats_2025_agg.get('current_H_since_last_HR', 0)
    expected_h_per_hr_from_stats = stats_2024_hitter.get('H_per_HR')
    
    if not pd.notna(expected_h_per_hr_from_stats) or expected_h_per_hr_from_stats <= 0:
        h_2025_agg = batter_stats_2025_agg.get('H', 0)
        hr_2025_agg = batter_stats_2025_agg.get('HR', 0)
        
        if hr_2025_agg > 0:
            expected_h_per_hr_from_stats = h_2025_agg / hr_2025_agg
        else:
            expected_h_per_hr_from_stats = 10.0  # Default
    
    details_dict.update({
        'h_since_last_hr': current_h_since_hr_val,
        'expected_h_per_hr': round(expected_h_per_hr_from_stats, 1)
    })
    
    if expected_h_per_hr_from_stats > 0 and current_h_since_hr_val > expected_h_per_hr_from_stats * 1.5:
        due_for_hr_hits_score = min(((current_h_since_hr_val / expected_h_per_hr_from_stats) - 1.5) * 15, 20)
    
    contextual_score += ENHANCED_WEIGHTS['due_for_hr_hits_factor'] * (due_for_hr_hits_score / 20 if due_for_hr_hits_score != 0 else 0)
    
    # ISO trend 2024 vs 2025
    trend_2025v2024_score = 0
    iso_2025_adj_for_trend_val = details_dict.get('batter_iso_adj', -1)
    
    K_PA_THRESHOLD_FOR_LEAGUE_AVG = 30
    if ab_2024_val >= K_PA_THRESHOLD_FOR_LEAGUE_AVG and batter_pa_2025 >= K_PA_THRESHOLD_FOR_LEAGUE_AVG / 2:
        iso_2024_val = (stats_2024_hitter.get('SLG', 0) - stats_2024_hitter.get('AVG', 0)) if ('SLG' in stats_2024_hitter and 'AVG' in stats_2024_hitter and stats_2024_hitter.get('AB', 0) > 0) else -1
        
        if iso_2024_val > -0.5 and iso_2025_adj_for_trend_val > -0.5:
            iso_change_from_last_year = iso_2025_adj_for_trend_val - iso_2024_val
            trend_2025v2024_score = iso_change_from_last_year * 150
            
            details_dict.update({
                'iso_2024': round(iso_2024_val, 3),
                'iso_2025_adj_for_trend': round(iso_2025_adj_for_trend_val, 3),
                'iso_trend_2025v2024': round(iso_change_from_last_year, 3)
            })
    
    contextual_score += ENHANCED_WEIGHTS['trend_2025_vs_2024_bonus'] * (trend_2025v2024_score / 20 if trend_2025v2024_score != 0 else 0)
    
    # Contact quality trend factors
    heating_up_contact_score = 0
    cold_batter_contact_score = 0
    MIN_RECENT_PA_FOR_CONTACT_EVAL = 20
    
    if recent_batter_stats and recent_batter_stats.get('total_pa_approx', 0) >= MIN_RECENT_PA_FOR_CONTACT_EVAL:
        recent_hit_rate = recent_batter_stats.get('hit_rate', -1)
        recent_hr_per_pa = recent_batter_stats.get('hr_per_pa', -1)
        
        if recent_hit_rate != -1:
            lg_avg_batting = league_avg_stats.get('AVG', 0.245)
            player_expected_hr_rate_for_comparison = expected_hr_per_ab_val
            
            # The player is making good contact but not getting HRs - could be due
            if (recent_hit_rate > (lg_avg_batting + 0.050) and
                recent_hr_per_pa != -1 and player_expected_hr_rate_for_comparison > 0 and
                recent_hr_per_pa < (player_expected_hr_rate_for_comparison * 0.4)):
                heating_up_contact_score = 15
                details_dict['contact_trend'] = 'Heating Up (High Contact, Low Recent Power)'
            # Player in cold streak, less likely for HR
            elif recent_hit_rate < (lg_avg_batting - 0.060):
                cold_batter_contact_score = -20
                details_dict['contact_trend'] = 'Cold Batter (Low Recent Contact)'
                
            # Apply modifiers
            if heating_up_contact_score > 0:
                contextual_score += ENHANCED_WEIGHTS['heating_up_contact_factor'] * (heating_up_contact_score / 15)
            if cold_batter_contact_score < 0:
                contextual_score += ENHANCED_WEIGHTS['cold_batter_factor'] * (cold_batter_contact_score / 20)
    
    details_dict.update({
        'heating_up_contact_raw_score': round(heating_up_contact_score, 1),
        'cold_batter_contact_raw_score': round(cold_batter_contact_score, 1),
        'due_for_hr_ab_raw_score': round(due_for_hr_ab_score, 1),
        'due_for_hr_hits_raw_score': round(due_for_hr_hits_score, 1),
        'trend_2025v2024_raw_score': round(trend_2025v2024_score, 1)
    })
    
    # 7. Calculate final score with dynamic weights
    final_score = (
        component_weights['arsenal_matchup'] * arsenal_score +
        component_weights['batter_overall'] * batter_overall_score +
        component_weights['pitcher_overall'] * pitcher_overall_score +
        component_weights['historical_yoy_csv'] * historical_score +
        component_weights['recent_daily_games'] * recent_score +
        component_weights['contextual'] * contextual_score
    )
    
    # Apply overall confidence adjustment to final score
    confidence_adjusted_score = final_score * overall_confidence + (45 * (1 - overall_confidence))
    
    base_prob_factor = confidence_adjusted_score / 100.0
    
    # Calculate pitcher per-game stats for display
    pitcher_stats_2025 = pitcher_data.get('stats_2025_aggregated', {})
    pitcher_games_2025 = pitcher_stats_2025.get('G', 1)  # Avoid division by zero
    
    # Check custom pitcher data for detailed stats first, then fallback to aggregated stats
    custom_pitcher_data = pitcher_data.get('custom_pitcher_stats', {})
    pitcher_overall_ev_data = pitcher_data.get('pitcher_overall_ev_stats', {})
    
    # Get detailed stats from custom data
    custom_games = custom_pitcher_data.get('p_game', pitcher_games_2025)
    custom_strikeouts = custom_pitcher_data.get('strikeout', pitcher_stats_2025.get('K', 0))
    custom_hits = custom_pitcher_data.get('hit', pitcher_stats_2025.get('H', 0))
    custom_walks = custom_pitcher_data.get('walk', pitcher_stats_2025.get('BB', 0))
    custom_ip_str = custom_pitcher_data.get('p_formatted_ip', '0.0')
    
    # Parse innings pitched (format like "27.2" = 27.67 innings)
    try:
        if '.' in str(custom_ip_str):
            ip_parts = str(custom_ip_str).split('.')
            innings = float(ip_parts[0]) + (float(ip_parts[1]) / 3.0) if len(ip_parts) > 1 else float(ip_parts[0])
        else:
            innings = float(custom_ip_str) if custom_ip_str else 1.0
    except:
        innings = 1.0
    
    # Pitcher per-game calculations using custom data when available
    pitcher_h_per_game = custom_hits / max(custom_games, 1)
    pitcher_hr_per_game = pitcher_stats_2025.get('HR', 0) / max(pitcher_games_2025, 1)
    pitcher_k_per_game = custom_strikeouts / max(custom_games, 1)
    
    # ERA from custom data
    pitcher_era = (custom_pitcher_data.get('p_era') or 
                   pitcher_overall_ev_data.get('p_era') or 
                   pitcher_stats_2025.get('ERA', 4.50))  # Default to league average ERA
    
    # Calculate WHIP from custom data: (Walks + Hits) / Innings Pitched
    if innings > 0 and (custom_hits > 0 or custom_walks > 0):
        pitcher_whip = (custom_walks + custom_hits) / innings
    else:
        pitcher_whip = (custom_pitcher_data.get('whip') or 
                        pitcher_overall_ev_data.get('whip') or 
                        pitcher_stats_2025.get('WHIP', 1.30))  # Default to league average WHIP
    
    # Pitcher home stats - estimate from total stats since we don't have home/road splits
    # Note: In real implementation, would need to aggregate daily games by venue
    total_games = pitcher_games_2025
    estimated_home_games = max(total_games * 0.5, 1)  # Assume roughly half games at home
    
    # Estimate home stats proportionally
    pitcher_home_h_total = round(pitcher_stats_2025.get('H', 0) * 0.5)
    pitcher_home_hr_total = round(pitcher_stats_2025.get('HR', 0) * 0.5)  
    pitcher_home_k_total = round(pitcher_stats_2025.get('K', 0) * 0.5)
    pitcher_home_games = round(estimated_home_games)
    
    # Recent ERA (last 5 starts) - would need more detailed game-by-game data
    # For now, use current season ERA as approximation
    pitcher_recent_era = pitcher_era
    
    return {
        'batter_name': batter_name,
        'batter_team': batter_roster_info.get('team', 'N/A'),
        'pitcher_name': pitcher_name,
        'pitcher_team': pitcher_roster_info.get('team', 'N/A'),
        'batter_hand': batter_hand,
        'pitcher_hand': pitcher_hand,
        'score': round(confidence_adjusted_score, 2),
        'original_score': round(final_score, 2),
        'confidence': round(overall_confidence, 3),
        'data_source': data_source,
        'details': details_dict,
        'component_breakdown': {
            'arsenal_matchup': round(arsenal_score, 1),
            'batter_overall': round(batter_overall_score, 1),
            'pitcher_overall': round(pitcher_overall_score, 1),
            'historical_yoy_csv': round(historical_score, 1),
            'recent_daily_games': round(recent_score, 1),
            'contextual': round(contextual_score, 1)
        },
        'matchup_components': {
            'arsenal_matchup': round(arsenal_score, 1),
            'batter_overall': round(batter_overall_score, 1),
            'pitcher_overall': round(pitcher_overall_score, 1),
            'historical_yoy_csv': round(historical_score, 1),
            'recent_daily_games': round(recent_score, 1),
            'contextual': round(contextual_score, 1)
        },
        'weights_used': component_weights,
        'outcome_probabilities': {
            'homerun': min(40, max(0.5, base_prob_factor * 10 + batter_pa_2025 * 0.005)),
            'hit': min(60, max(5, base_prob_factor * 20 + batter_pa_2025 * 0.02)),
            'reach_base': min(70, max(8, base_prob_factor * 25 + batter_pa_2025 * 0.03)),
            'strikeout': max(10, min(80, 70 - base_prob_factor * 15 + batter_pa_2025 * 0.01))
        },
        'recent_N_games_raw_data': recent_N_games_raw_data,
        'data_quality_summary': {
            'pitcher_arsenal_availability': 'full' if overall_confidence >= 0.8 else 'partial' if overall_confidence >= 0.5 else 'minimal',
            'fallback_strategy': data_source,
            'reliability_indicator': 'high' if overall_confidence >= 0.7 else 'medium' if overall_confidence >= 0.4 else 'low'
        },
        # Pitcher stats for UI display
        'pitcher_h_per_game': round(pitcher_h_per_game, 1),
        'pitcher_hr_per_game': round(pitcher_hr_per_game, 1),
        'pitcher_k_per_game': round(pitcher_k_per_game, 1),
        'pitcher_era': round(pitcher_era, 2),
        'pitcher_whip': round(pitcher_whip, 2),
        'pitcher_recent_era': round(pitcher_recent_era, 2),
        'pitcher_home_h_total': round(pitcher_home_h_total, 0),
        'pitcher_home_hr_total': round(pitcher_home_hr_total, 0),
        'pitcher_home_k_total': round(pitcher_home_k_total, 0),
        'pitcher_home_games': round(pitcher_home_games, 0)
    }

def analyze_historical_trends_general(player_id, historical_data, data_source_key, 
                                     relevant_metrics, pitch_type_filter=None, current_year=2025):
    """
    Analyze year-over-year trends for a player across specified metrics.
    (This function remains unchanged from the original analyzer.py)
    """
    trends = {}
    yearly_values = defaultdict(lambda: defaultdict(list))
    
    sorted_years = sorted([yr for yr in historical_data.keys() if yr < current_year])
    
    for year in sorted_years:
        if data_source_key not in historical_data.get(year, {}):
            continue
            
        df = historical_data[year][data_source_key]
        player_rows = df[df['mlbam_id'] == str(player_id)]
        
        if pitch_type_filter and 'pitch_type' in player_rows.columns:
            player_rows = player_rows[player_rows['pitch_type'] == pitch_type_filter]
            
        if not player_rows.empty:
            for metric in relevant_metrics:
                if metric in player_rows.columns:
                    value = player_rows.iloc[0].get(metric)
                    if pd.notna(value):
                        yearly_values[metric][year].append(value)
    
    for metric, year_data in yearly_values.items():
        averaged_values = {yr: np.mean(vals) for yr, vals in year_data.items() if vals}
        
        if len(averaged_values) >= 2:
            sorted_years_with_data = sorted(averaged_values.keys())
            chronological_values = [averaged_values[yr] for yr in sorted_years_with_data]
            
            recent_value = chronological_values[-1]
            early_value = chronological_values[0]
            
            direction = "improving" if recent_value > early_value else "declining" if recent_value < early_value else "stable"
            magnitude = abs(recent_value - early_value)
            consistency = np.std(chronological_values) if len(chronological_values) > 1 else 0
            
            trends[metric] = {
                'direction': direction,
                'magnitude': magnitude,
                'recent_value': recent_value,
                'early_value': early_value,
                'historical_values': averaged_values,
                'consistency_std': consistency
            }
    
    return trends

def calculate_general_historical_bonus(trends_dict):
    """Calculate a bonus score based on historical trends."""
    if not trends_dict:
        return 0
    
    num_metrics = 0
    total_impact = 0
    total_consistency = 0
    
    for metric, trend_data in trends_dict.items():
        num_metrics += 1
        scaled_magnitude = trend_data['magnitude'] * 100
        
        if trend_data['direction'] == 'improving':
            total_impact += scaled_magnitude
        elif trend_data['direction'] == 'declining':
            total_impact -= scaled_magnitude
            
        consistency = trend_data.get('consistency_std', 1.0)
        if consistency < 0.03:
            total_consistency += (5 if trend_data['direction'] != 'declining' else -3)
        elif consistency > 0.12:
            total_consistency -= 3
    
    if num_metrics > 0:
        bonus = (total_impact / num_metrics) + (total_consistency / num_metrics)
    else:
        bonus = 0
        
    return min(max(bonus, -25), 25)

def calculate_recent_performance_bonus(recent_stats, player_type='hitter'):
    """Calculate a bonus score based on recent performance trends."""
    if not recent_stats or recent_stats.get('total_games', 0) < 2:
        return 0
    
    bonus = 0
    
    if player_type == 'hitter':
        # HR rate trend
        trend_magnitude = recent_stats.get('trend_magnitude', 0)
        if recent_stats.get('trend_direction') == 'improving':
            bonus += 15 * trend_magnitude * 100
        elif recent_stats.get('trend_direction') == 'declining':
            bonus -= 12 * trend_magnitude * 100
        
        # Recent HR rate level
        hr_per_pa = recent_stats.get('hr_per_pa', 0)
        if hr_per_pa > 0.05:
            bonus += 20
        elif hr_per_pa > 0.03:
            bonus += 10
        elif hr_per_pa < 0.01 and recent_stats.get('total_pa_approx', 0) > 20:
            bonus -= 10
            
        # Overall performance
        avg_performance = recent_stats.get('avg_avg', 0)
        if avg_performance > 0.300:
            bonus += 15
        elif avg_performance > 0.275:
            bonus += 8
        elif avg_performance < 0.200 and recent_stats.get('total_ab', 0) > 10:
            bonus -= 12
            
        # Contact trend
        hit_rate_trend = recent_stats.get('hit_rate_trend', {})
        if hit_rate_trend.get('direction') == 'improving' and hit_rate_trend.get('magnitude', 0) > 0.050:
            bonus += 10
    
    return min(max(bonus, -30), 30)