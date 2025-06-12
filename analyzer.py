import numpy as np
import pandas as pd
from collections import defaultdict
from utils import (
    normalize_calculated, 
    adjust_stat_with_confidence,
    get_approximated_pa
)

# Default weights for analysis
WEIGHTS = {
    'batter_vs_pitch_slg': 1.5, 'batter_vs_pitch_hr': 2.0, 'batter_vs_pitch_hard_hit': 1.0,
    'batter_batted_ball_fb': 0.8, 'batter_batted_ball_pull_air': 1.2,
    'pitcher_vulnerability_slg': 1.2, 'pitcher_vulnerability_hr': 1.8, 'pitcher_vulnerability_hard_hit': 0.8,
    'pitcher_run_value_penalty': 1.0,
    'batter_overall_brl_percent': 2.5, 'batter_overall_hard_hit': 1.2, 'batter_overall_iso': 1.5,
    'pitcher_overall_brl_percent_allowed': 2.0, 'pitcher_overall_hard_hit_allowed': 1.0,
    'historical_trend_bonus': 0.7, 'historical_consistency_bonus': 0.3,
    'recent_performance_bonus': 1.5,
    'ev_matchup_bonus': 1.0,
    'due_for_hr_factor': 0.5,         # AB-based due factor
    'due_for_hr_hits_factor': 0.3,    # Hits-based due factor
    'heating_up_contact_factor': 0.4, # Bonus if high contact, low recent HR
    'cold_batter_factor': 0.4,        # Penalty if very low recent contact
    'hitter_pitch_rv_advantage': 0.8, 'hitter_pitch_k_avoidance': 0.4,
    'pitcher_pitch_k_ability': 0.4,
    'trend_2025_vs_2024_bonus': 0.8,
}

# Component weights for final score
W_ARSENAL_MATCHUP = 0.40
W_BATTER_OVERALL = 0.15
W_PITCHER_OVERALL = 0.10
W_HISTORICAL_YOY_CSV = 0.05
W_RECENT_DAILY_GAMES = 0.10
W_CONTEXTUAL = 0.20

# Constants
DEFAULT_EXPECTED_H_PER_HR = 10.0  # Approx 1 HR every 10 hits as a fallback
MIN_RECENT_PA_FOR_CONTACT_EVAL = 20  # Min PA in recent games to evaluate contact trends
K_PA_THRESHOLD_FOR_LEAGUE_AVG = 30
K_PA_WARNING_THRESHOLD = 50

def calculate_recent_trends(games_performance):
    """
    Calculate performance trends from a player's recent games.
    Returns a dictionary of aggregated stats and trend information.
    """
    if not games_performance:
        return {}
    
    num_games = len(games_performance)
    
    # Calculate totals across all games
    total_ab = sum(g['AB'] for g in games_performance)
    total_h = sum(g['H'] for g in games_performance)
    total_hr = sum(g['HR'] for g in games_performance)
    total_bb = sum(g['BB'] for g in games_performance)
    total_k = sum(g['K'] for g in games_performance)
    total_pa_approx = sum(get_approximated_pa(g) for g in games_performance)
    
    # Calculate averages and rates
    recent_stats = {
        'total_games': num_games,
        'total_ab': total_ab,
        'total_hits': total_h,
        'total_hrs': total_hr,
        'total_bb': total_bb,
        'total_k': total_k,
        'total_pa_approx': total_pa_approx,
        'avg_avg': np.mean([g['AVG'] for g in games_performance if g['AB'] > 0]) if any(g['AB'] > 0 for g in games_performance) else 0,
        'avg_obp': np.mean([g['OBP'] for g in games_performance if get_approximated_pa(g) > 0]) if any(get_approximated_pa(g) > 0 for g in games_performance) else 0,
        'avg_slg': np.mean([g['SLG'] for g in games_performance if g['AB'] > 0]) if any(g['AB'] > 0 for g in games_performance) else 0,
        'hit_rate': total_h / total_ab if total_ab > 0 else 0,
        'hr_rate': total_hr / total_ab if total_ab > 0 else 0,
        'hr_per_pa': total_hr / total_pa_approx if total_pa_approx > 0 else 0,
        'k_rate': total_k / total_pa_approx if total_pa_approx > 0 else 0,
        'bb_rate': total_bb / total_pa_approx if total_pa_approx > 0 else 0,
        'obp_calc': (total_h + total_bb) / total_pa_approx if total_pa_approx > 0 else 0
    }
    
    # Calculate trends (first half vs second half)
    if num_games >= 2:
        mid_point = num_games // 2
        recent_half_games = games_performance[:mid_point]  # More recent games
        earlier_half_games = games_performance[mid_point:]  # Earlier games
        
        if recent_half_games and earlier_half_games:
            # HR/PA trend
            recent_hr_trend = sum(g['HR'] for g in recent_half_games)
            recent_pa_trend = sum(get_approximated_pa(g) for g in recent_half_games)
            recent_val = recent_hr_trend / recent_pa_trend if recent_pa_trend > 0 else 0
            
            early_hr_trend = sum(g['HR'] for g in earlier_half_games)
            early_pa_trend = sum(get_approximated_pa(g) for g in earlier_half_games)
            early_val = early_hr_trend / early_pa_trend if early_pa_trend > 0 else 0
            
            recent_stats.update({
                'trend_metric': 'HR_per_PA',
                'trend_recent_val': round(recent_val, 3),
                'trend_early_val': round(early_val, 3),
                'trend_direction': 'improving' if recent_val > early_val else 'declining' if recent_val < early_val else 'stable',
                'trend_magnitude': abs(recent_val - early_val)
            })
            
            # Alternative trend: Contact quality
            recent_hits = sum(g['H'] for g in recent_half_games)
            recent_abs = sum(g['AB'] for g in recent_half_games)
            recent_hit_rate = recent_hits / recent_abs if recent_abs > 0 else 0
            
            early_hits = sum(g['H'] for g in earlier_half_games)
            early_abs = sum(g['AB'] for g in earlier_half_games)
            early_hit_rate = early_hits / early_abs if early_abs > 0 else 0
            
            recent_stats.update({
                'hit_rate_trend': {
                    'early_val': round(early_hit_rate, 3),
                    'recent_val': round(recent_hit_rate, 3),
                    'direction': 'improving' if recent_hit_rate > early_hit_rate else 'declining' if recent_hit_rate < early_hit_rate else 'stable',
                    'magnitude': abs(recent_hit_rate - early_hit_rate)
                }
            })
    
    return recent_stats

def analyze_historical_trends_general(player_id, historical_data, data_source_key_in_historical_data, 
                                     relevant_metrics_list, pitch_type_filter=None, current_prediction_year=2025):
    """
    Analyze year-over-year trends for a player across specified metrics.
    Returns a dictionary of trend data for each metric.
    """
    trends = {}
    yearly_metric_values_collector = defaultdict(lambda: defaultdict(list))
    
    sorted_historical_years = sorted([yr for yr in historical_data.keys() if yr < current_prediction_year])
    
    for year in sorted_historical_years:
        if data_source_key_in_historical_data not in historical_data.get(year, {}):
            continue
            
        df_for_year = historical_data[year][data_source_key_in_historical_data]
        player_rows_for_year = df_for_year[df_for_year['mlbam_id'] == str(player_id)]
        
        if pitch_type_filter and 'pitch_type' in player_rows_for_year.columns:
            player_rows_for_year = player_rows_for_year[player_rows_for_year['pitch_type'] == pitch_type_filter]
            
        if not player_rows_for_year.empty:
            for metric_column_name in relevant_metrics_list:
                if metric_column_name in player_rows_for_year.columns:
                    value = player_rows_for_year.iloc[0].get(metric_column_name)
                    if pd.notna(value):
                        yearly_metric_values_collector[metric_column_name][year].append(value)
    
    for metric, year_data_map in yearly_metric_values_collector.items():
        averaged_yearly_values = {yr: np.mean(vals) for yr, vals in year_data_map.items() if vals}
        
        if len(averaged_yearly_values) >= 2:
            sorted_years_with_data = sorted(averaged_yearly_values.keys())
            chronological_values_for_metric = [averaged_yearly_values[yr] for yr in sorted_years_with_data]
            
            recent_value = chronological_values_for_metric[-1]
            early_value = chronological_values_for_metric[0]
            
            direction = "improving" if recent_value > early_value else "declining" if recent_value < early_value else "stable"
            magnitude_of_change = abs(recent_value - early_value)
            consistency_std_dev = np.std(chronological_values_for_metric) if len(chronological_values_for_metric) > 1 else 0
            
            trends[metric] = {
                'direction': direction,
                'magnitude': magnitude_of_change,
                'recent_value': recent_value,
                'early_value': early_value,
                'historical_values_map': averaged_yearly_values,
                'consistency_std': consistency_std_dev
            }
    
    return trends

def calculate_general_historical_bonus(trends_dict):
    """Calculate a bonus score based on historical trends."""
    if not trends_dict:
        return 0
    
    num_metrics_considered = 0
    total_scaled_impact_points = 0
    total_consistency_points = 0
    
    for metric, trend_data in trends_dict.items():
        num_metrics_considered += 1
        scaled_magnitude_impact = trend_data['magnitude'] * 100  # Example scaling
        
        if trend_data['direction'] == 'improving':
            total_scaled_impact_points += scaled_magnitude_impact
        elif trend_data['direction'] == 'declining':
            total_scaled_impact_points -= scaled_magnitude_impact
            
        consistency_std = trend_data.get('consistency_std', 1.0)
        if consistency_std < 0.03:
            # Reward consistency if not declining
            total_consistency_points += (5 if trend_data['direction'] != 'declining' else -3)
        elif consistency_std > 0.12:
            # Penalize high volatility
            total_consistency_points -= 3
    
    if num_metrics_considered > 0:
        bonus = (total_scaled_impact_points / num_metrics_considered) + (total_consistency_points / num_metrics_considered)
    else:
        bonus = 0
        
    return min(max(bonus, -25), 25)  # Cap bonus/penalty

def calculate_recent_performance_bonus(recent_stats, player_type='hitter'):
    """Calculate a bonus score based on recent performance trends."""
    if not recent_stats or recent_stats.get('total_games', 0) < 2:
        return 0
    
    bonus = 0
    
    if player_type == 'hitter':
        # Trend in HR rate
        trend_magnitude_hr_rate = recent_stats.get('trend_magnitude', 0)
        if recent_stats.get('trend_direction') == 'improving':
            bonus += 15 * trend_magnitude_hr_rate * 100
        elif recent_stats.get('trend_direction') == 'declining':
            bonus -= 12 * trend_magnitude_hr_rate * 100
        
        # Recent HR rate level
        hr_per_pa_recent = recent_stats.get('hr_per_pa', 0)
        if hr_per_pa_recent > 0.05:
            bonus += 20  # Strong recent HR rate
        elif hr_per_pa_recent > 0.03:
            bonus += 10
        elif hr_per_pa_recent < 0.01 and recent_stats.get('total_pa_approx', 0) > 20:
            bonus -= 10  # Very low recent HR rate
            
        # Hitting streak factor from enhanced script
        avg_performance = recent_stats.get('avg_avg', 0)
        if avg_performance > 0.300:
            bonus += 15
        elif avg_performance > 0.275:
            bonus += 8
        elif avg_performance < 0.200 and recent_stats.get('total_ab', 0) > 10:
            bonus -= 12
            
        # Contact quality trend
        hit_rate_trend = recent_stats.get('hit_rate_trend', {})
        if hit_rate_trend.get('direction') == 'improving' and hit_rate_trend.get('magnitude', 0) > 0.050:
            bonus += 10  # Significant improvement in contact quality
        
    return min(max(bonus, -30), 30)  # Cap bonus/penalty

def analyze_pitch_arsenal_matchup(batter_id, pitcher_id, master_player_data, current_year=2025):
    """
    Detailed analysis of the matchup between a batter and pitcher's arsenal.
    Returns a dictionary of matchup details by pitch type and overall metrics.
    """
    batter_data = master_player_data.get(str(batter_id))
    pitcher_data = master_player_data.get(str(pitcher_id))
    
    if not batter_data or not pitcher_data:
        return {
            "error": "Batter or pitcher data not found.",
            "pitch_matchups": [],
            "overall_summary_metrics": {}
        }
    
    pitcher_arsenal_stats_2025 = pitcher_data.get('pitcher_pitch_arsenal_stats', {})
    pitcher_usage_percentages_2025 = pitcher_data.get('pitch_usage_stats', {})
    
    if not pitcher_usage_percentages_2025:
        return {
            "error": "Pitcher usage data for 2025 not found.",
            "pitch_matchups": [],
            "overall_summary_metrics": {}
        }
    
    matchup_details_by_pitch_type = []
    weighted_average_metrics_accumulator = defaultdict(lambda: {'sum_weighted_values': 0, 'sum_weights': 0})
    
    metrics_to_analyze_from_arsenal = ['ba', 'slg', 'woba', 'hard_hit_percent', 'k_percent', 'run_value_per_100']
    
    for pitch_type_abbr, usage_percent_value in pitcher_usage_percentages_2025.items():
        if usage_percent_value < 5:
            continue  # Min usage threshold
            
        usage_weight_factor = usage_percent_value / 100.0
        
        pitch_matchup_output_info = {
            'pitch_type': pitch_type_abbr,
            'pitch_name': pitcher_arsenal_stats_2025.get(pitch_type_abbr, {}).get('pitch_name', pitch_type_abbr),
            'usage': usage_percent_value
        }
        
        hitter_stats_vs_pitch_type_2025 = batter_data.get('hitter_pitch_arsenal_stats', {}).get(pitch_type_abbr, {})
        pitcher_stats_with_pitch_type_2025 = pitcher_arsenal_stats_2025.get(pitch_type_abbr, {})
        
        current_year_comparison_stats = {}
        
        for metric_key in metrics_to_analyze_from_arsenal:
            hitter_value = hitter_stats_vs_pitch_type_2025.get(metric_key)
            pitcher_value = pitcher_stats_with_pitch_type_2025.get(metric_key)
            
            # Normalize percentage values
            if metric_key in ['hard_hit_percent', 'k_percent'] and hitter_value is not None and pd.notna(hitter_value):
                hitter_value /= 100.0
            if metric_key in ['hard_hit_percent', 'k_percent'] and pitcher_value is not None and pd.notna(pitcher_value):
                pitcher_value /= 100.0
            
            current_year_comparison_stats[f'hitter_{metric_key}'] = hitter_value
            current_year_comparison_stats[f'pitcher_{metric_key}'] = pitcher_value
            
            # Accumulate weighted values for overall metrics
            if pd.notna(hitter_value):
                weighted_average_metrics_accumulator[f'hitter_avg_{metric_key}']['sum_weighted_values'] += hitter_value * usage_weight_factor
                weighted_average_metrics_accumulator[f'hitter_avg_{metric_key}']['sum_weights'] += usage_weight_factor
            
            if pd.notna(pitcher_value):
                weighted_average_metrics_accumulator[f'pitcher_avg_{metric_key}']['sum_weighted_values'] += pitcher_value * usage_weight_factor
                weighted_average_metrics_accumulator[f'pitcher_avg_{metric_key}']['sum_weights'] += usage_weight_factor
        
        pitch_matchup_output_info['current_year_stats'] = current_year_comparison_stats
        
        # Add to output
        matchup_details_by_pitch_type.append(pitch_matchup_output_info)
    
    # Calculate overall weighted metrics
    overall_summary_metrics_calculated = {}
    for metric_name_avg, data_sums in weighted_average_metrics_accumulator.items():
        overall_summary_metrics_calculated[metric_name_avg] = data_sums['sum_weighted_values'] / data_sums['sum_weights'] if data_sums['sum_weights'] > 0 else None
    
    return {
        "pitch_matchups": matchup_details_by_pitch_type,
        "overall_summary_metrics": overall_summary_metrics_calculated,
        "batter_id": batter_id,
        "pitcher_id": pitcher_id
    }

def enhanced_hr_likelihood_score(batter_mlbam_id, pitcher_mlbam_id, master_player_data, 
                                historical_data, metric_ranges, league_avg_stats, recent_batter_stats=None):
    """
    Comprehensive HR likelihood score calculation.
    Returns a dictionary with score details and component breakdowns.
    """
    batter_data = master_player_data.get(str(batter_mlbam_id))
    pitcher_data = master_player_data.get(str(pitcher_mlbam_id))
    
    if not batter_data or not pitcher_data:
        return {'score': 0, 'reason': "Missing player master data"}
    
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
    
    batter_pa_warning_msg = f" (Low PA_2025: {batter_pa_2025})" if batter_pa_2025 < K_PA_WARNING_THRESHOLD else ""
    details_for_output_dict = {'batter_pa_2025': batter_pa_2025, 'batter_pa_warning': batter_pa_warning_msg}
    
    # 1. Arsenal analysis
    arsenal_analysis_result = analyze_pitch_arsenal_matchup(batter_mlbam_id, pitcher_mlbam_id, master_player_data)
    details_for_output_dict['arsenal_analysis'] = arsenal_analysis_result
    
    avg_matchup_score_from_arsenal = 0
    if "error" not in arsenal_analysis_result and arsenal_analysis_result.get('pitch_matchups'):
        hitter_weighted_slg_vs_arsenal = arsenal_analysis_result.get('overall_summary_metrics', {}).get('hitter_avg_slg')
        pitcher_weighted_slg_allowed_with_arsenal = arsenal_analysis_result.get('overall_summary_metrics', {}).get('pitcher_avg_slg')
        
        if hitter_weighted_slg_vs_arsenal is not None and pitcher_weighted_slg_allowed_with_arsenal is not None:
            norm_h_wslg = normalize_calculated(hitter_weighted_slg_vs_arsenal, 'slg', metric_ranges, higher_is_better=True)
            norm_p_wslg_a = normalize_calculated(pitcher_weighted_slg_allowed_with_arsenal, 'slg', metric_ranges, higher_is_better=True)
            avg_matchup_score_from_arsenal = (norm_h_wslg * 0.6 + norm_p_wslg_a * 0.4)
        else:
            avg_matchup_score_from_arsenal = 30
    else:
        avg_matchup_score_from_arsenal = 25
        if "error" in arsenal_analysis_result:
            details_for_output_dict['arsenal_analysis_error'] = arsenal_analysis_result["error"]
    
    # 2. Batter overall evaluation
    batter_overall_score_component = 0
    hitter_overall_ev_stats = batter_data.get('hitter_overall_ev_stats', {})
    
    if isinstance(hitter_overall_ev_stats, dict):
        iso_overall_adj = adjust_stat_with_confidence(
            hitter_overall_ev_stats.get('iso_percent'),
            batter_pa_2025,
            'ISO',
            league_avg_stats,
            default_league_avg_override=league_avg_stats['ISO']
        )
        
        brl_overall_raw = (hitter_overall_ev_stats.get('brl_percent') / 100.0) if pd.notna(hitter_overall_ev_stats.get('brl_percent')) else league_avg_stats['AVG_BRL_PERCENT']
        hh_overall_raw = (hitter_overall_ev_stats.get('hard_hit_percent') / 100.0) if pd.notna(hitter_overall_ev_stats.get('hard_hit_percent')) else league_avg_stats['AVG_HARD_HIT_PERCENT']
        
        batter_overall_score_component += WEIGHTS['batter_overall_iso'] * normalize_calculated(iso_overall_adj, 'iso', metric_ranges)
        batter_overall_score_component += WEIGHTS['batter_overall_brl_percent'] * normalize_calculated(brl_overall_raw, 'brl_percent', metric_ranges)
        batter_overall_score_component += WEIGHTS['batter_overall_hard_hit'] * normalize_calculated(hh_overall_raw, 'hard_hit_percent', metric_ranges)
        
        details_for_output_dict.update({
            'batter_overall_adj_iso': round(iso_overall_adj if pd.notna(iso_overall_adj) else 0, 3),
            'batter_overall_brl': round(brl_overall_raw, 3),
            'batter_overall_hh': round(hh_overall_raw, 3)
        })
    
    # 3. Pitcher overall evaluation
    pitcher_overall_score_component = 0
    pitcher_overall_ev_stats = pitcher_data.get('pitcher_overall_ev_stats', {})
    
    if isinstance(pitcher_overall_ev_stats, dict):
        brl_allowed_raw = (pitcher_overall_ev_stats.get('brl_percent') / 100.0) if pd.notna(pitcher_overall_ev_stats.get('brl_percent')) else league_avg_stats['AVG_BRL_PERCENT']
        hh_allowed_raw = (pitcher_overall_ev_stats.get('hard_hit_percent') / 100.0) if pd.notna(pitcher_overall_ev_stats.get('hard_hit_percent')) else league_avg_stats['AVG_HARD_HIT_PERCENT']
        
        pitcher_overall_score_component += WEIGHTS['pitcher_overall_brl_percent_allowed'] * normalize_calculated(brl_allowed_raw, 'brl_percent', metric_ranges, higher_is_better=True)
        pitcher_overall_score_component += WEIGHTS['pitcher_overall_hard_hit_allowed'] * normalize_calculated(hh_allowed_raw, 'hard_hit_percent', metric_ranges, higher_is_better=True)
        
        details_for_output_dict.update({
            'pitcher_overall_brl_allowed': round(brl_allowed_raw, 3),
            'pitcher_overall_hh_allowed': round(hh_allowed_raw, 3)
        })
    
    # 4. Historical year-over-year analysis
    historical_trends_for_hitter = analyze_historical_trends_general(
        str(batter_mlbam_id),
        historical_data,
        'hitter_arsenal',
        ['slg', 'woba'],
        pitch_type_filter=None
    )
    
    historical_yoy_csv_score = calculate_general_historical_bonus(historical_trends_for_hitter)
    
    # Collect the historical metrics for display
    historical_metrics_details = []
    for metric, trend_info in historical_trends_for_hitter.items():
        if trend_info['direction'] != 'stable':
            historical_metrics_details.append({
                'metric': metric,
                'direction': trend_info['direction'],
                'early_value': round(trend_info['early_value'], 3),
                'recent_value': round(trend_info['recent_value'], 3),
                'magnitude': round(trend_info['magnitude'], 3)
            })
    details_for_output_dict['historical_metrics'] = historical_metrics_details
    
    # 5. Recent performance analysis
    recent_daily_games_score = calculate_recent_performance_bonus(recent_batter_stats, 'hitter')
    
    # 6. Contextual factors analysis
    contextual_factors_total_score = 0
    
    # 6a. Exit velocity matchup
    ev_matchup_sub_score = 0
    if isinstance(hitter_overall_ev_stats, dict) and isinstance(pitcher_overall_ev_stats, dict):
        h_hh_val = hitter_overall_ev_stats.get('hard_hit_percent', league_avg_stats['AVG_HARD_HIT_PERCENT'] * 100)
        p_hh_val_allowed = pitcher_overall_ev_stats.get('hard_hit_percent', league_avg_stats['AVG_HARD_HIT_PERCENT'] * 100)
        
        norm_h_hh = normalize_calculated(h_hh_val / 100.0, 'hard_hit_percent', metric_ranges, higher_is_better=True)
        norm_p_hh_allowed_is_good_for_hitter = normalize_calculated(p_hh_val_allowed / 100.0, 'hard_hit_percent', metric_ranges, higher_is_better=True)
        
        ev_matchup_sub_score = (norm_h_hh * 0.6 + norm_p_hh_allowed_is_good_for_hitter * 0.4) - 50
    
    contextual_factors_total_score += WEIGHTS['ev_matchup_bonus'] * (ev_matchup_sub_score / 50 if ev_matchup_sub_score != 0 else 0)
    details_for_output_dict['ev_matchup_raw_score'] = round(ev_matchup_sub_score, 1)
    
    # 6b. Due for HR based on AB count
    due_for_hr_ab_sub_score = 0
    stats_2024_hitter = batter_data.get('stats_2024', {})
    hr_2024_val, ab_2024_val = stats_2024_hitter.get('HR', 0), stats_2024_hitter.get('AB', 0)
    hr_2025_agg_val, ab_2025_agg_val = batter_stats_2025_agg.get('HR', 0), batter_stats_2025_agg.get('AB', 0)
    
    expected_hr_per_ab_val = 0
    if hr_2024_val > 0 and ab_2024_val >= 50:
        expected_hr_per_ab_val = hr_2024_val / ab_2024_val
    elif hr_2025_agg_val > 0 and ab_2025_agg_val >= 30:
        expected_hr_per_ab_val = hr_2025_agg_val / ab_2025_agg_val
    else:
        expected_hr_per_ab_val = 1 / 45.0
    
    if expected_hr_per_ab_val > 0:
        ab_needed_for_hr_val = 1 / expected_hr_per_ab_val
        current_ab_since_hr_val = batter_stats_2025_agg.get('current_AB_since_last_HR', 0)
        
        details_for_output_dict.update({
            'ab_since_last_hr': current_ab_since_hr_val,
            'expected_ab_per_hr': round(ab_needed_for_hr_val, 1)
        })
        
        if current_ab_since_hr_val > ab_needed_for_hr_val * 1.25:
            due_for_hr_ab_sub_score = min((current_ab_since_hr_val / ab_needed_for_hr_val - 1.25) * 20, 25)
    
    contextual_factors_total_score += WEIGHTS['due_for_hr_factor'] * (due_for_hr_ab_sub_score / 25 if due_for_hr_ab_sub_score != 0 else 0)
    details_for_output_dict['due_for_hr_ab_raw_score'] = round(due_for_hr_ab_sub_score, 1)
    
    # 6c. Due for HR based on hits count
    due_for_hr_hits_sub_score = 0
    current_h_since_hr_val = batter_stats_2025_agg.get('current_H_since_last_HR', 0)
    expected_h_per_hr_from_stats = stats_2024_hitter.get('H_per_HR')
    
    if not pd.notna(expected_h_per_hr_from_stats) or expected_h_per_hr_from_stats <= 0:
        h_2025_agg = batter_stats_2025_agg.get('H', 0)
        hr_2025_agg = batter_stats_2025_agg.get('HR', 0)
        
        if hr_2025_agg > 0:
            expected_h_per_hr_from_stats = h_2025_agg / hr_2025_agg
        else:
            expected_h_per_hr_from_stats = DEFAULT_EXPECTED_H_PER_HR
    
    details_for_output_dict.update({
        'h_since_last_hr': current_h_since_hr_val,
        'expected_h_per_hr': round(expected_h_per_hr_from_stats, 1)
    })
    
    if expected_h_per_hr_from_stats > 0 and current_h_since_hr_val > expected_h_per_hr_from_stats * 1.5:
        due_for_hr_hits_sub_score = min(((current_h_since_hr_val / expected_h_per_hr_from_stats) - 1.5) * 15, 20)
    
    contextual_factors_total_score += WEIGHTS['due_for_hr_hits_factor'] * (due_for_hr_hits_sub_score / 20 if due_for_hr_hits_sub_score != 0 else 0)
    details_for_output_dict['due_for_hr_hits_raw_score'] = round(due_for_hr_hits_sub_score, 1)
    
    # 6d. 2024 vs 2025 ISO trend
    trend_2025v2024_sub_score = 0
    iso_2025_adj_for_trend_val = details_for_output_dict.get('batter_overall_adj_iso', -1)
    
    if ab_2024_val >= K_PA_THRESHOLD_FOR_LEAGUE_AVG and batter_pa_2025 >= K_PA_THRESHOLD_FOR_LEAGUE_AVG / 2:
        iso_2024_val = (stats_2024_hitter.get('SLG', 0) - stats_2024_hitter.get('AVG', 0)) if ('SLG' in stats_2024_hitter and 'AVG' in stats_2024_hitter and stats_2024_hitter.get('AB', 0) > 0) else -1
        
        if iso_2024_val > -0.5 and iso_2025_adj_for_trend_val > -0.5:
            iso_change_from_last_year = iso_2025_adj_for_trend_val - iso_2024_val
            trend_2025v2024_sub_score = iso_change_from_last_year * 150
            
            details_for_output_dict.update({
                'iso_2024': round(iso_2024_val, 3),
                'iso_2025_adj_for_trend': round(iso_2025_adj_for_trend_val, 3),
                'iso_trend_2025v2024': round(iso_change_from_last_year, 3)
            })
    
    contextual_factors_total_score += WEIGHTS['trend_2025_vs_2024_bonus'] * (trend_2025v2024_sub_score / 20 if trend_2025v2024_sub_score != 0 else 0)
    details_for_output_dict['trend_2025v2024_raw_score'] = round(trend_2025v2024_sub_score, 1)
    
    # 6e. Contact quality trend factors
    heating_up_contact_sub_score = 0
    cold_batter_contact_sub_score = 0
    
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
                heating_up_contact_sub_score = 15
                details_for_output_dict['contact_trend'] = 'Heating Up (High Contact, Low Recent Power)'
            # Player in cold streak, less likely for HR
            elif recent_hit_rate < (lg_avg_batting - 0.060):
                cold_batter_contact_sub_score = -20
                details_for_output_dict['contact_trend'] = 'Cold Batter (Low Recent Contact)'
                
            # Apply modifiers
            if heating_up_contact_sub_score > 0:
                contextual_factors_total_score += WEIGHTS['heating_up_contact_factor'] * (heating_up_contact_sub_score / 15)
            if cold_batter_contact_sub_score < 0:
                contextual_factors_total_score += WEIGHTS['cold_batter_factor'] * (cold_batter_contact_sub_score / 20)
    
    details_for_output_dict['heating_up_contact_raw_score'] = round(heating_up_contact_sub_score, 1)
    details_for_output_dict['cold_batter_contact_raw_score'] = round(cold_batter_contact_sub_score, 1)
    
    # 7. Final score calculation
    final_hr_score_calculated = (
        W_ARSENAL_MATCHUP * avg_matchup_score_from_arsenal +
        W_BATTER_OVERALL * batter_overall_score_component +
        W_PITCHER_OVERALL * pitcher_overall_score_component +
        W_HISTORICAL_YOY_CSV * historical_yoy_csv_score +
        W_RECENT_DAILY_GAMES * recent_daily_games_score +
        W_CONTEXTUAL * contextual_factors_total_score
    )
    
    base_prob_factor = final_hr_score_calculated / 100.0
    
    # 8. Result object
    return {
        'batter_name': batter_name,
        'batter_team': batter_roster_info.get('team', 'N/A'),
        'pitcher_name': pitcher_name,
        'pitcher_team': pitcher_roster_info.get('team', 'N/A'),
        'batter_hand': batter_hand,
        'pitcher_hand': pitcher_hand,
        'score': round(final_hr_score_calculated, 2),
        'details': details_for_output_dict,
        'historical_summary': f"HistCSV Bonus:{historical_yoy_csv_score:.1f}",
        'recent_summary': f"RecentDaily Bonus:{recent_daily_games_score:.1f} (Trend:{recent_batter_stats.get('trend_metric', 'N/A')} {recent_batter_stats.get('trend_early_val', '')}->{recent_batter_stats.get('trend_recent_val', '')})" if recent_batter_stats else "No recent daily stats",
        'matchup_components': {
            'arsenal_matchup': round(avg_matchup_score_from_arsenal, 1),
            'batter_overall': round(batter_overall_score_component, 1),
            'pitcher_overall': round(pitcher_overall_score_component, 1),
            'historical_yoy_csv': round(historical_yoy_csv_score, 1),
            'recent_daily_games': round(recent_daily_games_score, 1),
            'contextual': round(contextual_factors_total_score, 1)
        },
        'outcome_probabilities': {
            'homerun': min(40, max(0.5, base_prob_factor * 10 + batter_pa_2025 * 0.005)),
            'hit': min(60, max(5, base_prob_factor * 20 + batter_pa_2025 * 0.02)),
            'reach_base': min(70, max(8, base_prob_factor * 25 + batter_pa_2025 * 0.03)),
            'strikeout': max(10, min(80, 70 - base_prob_factor * 15 + batter_pa_2025 * 0.01))
        }
    }