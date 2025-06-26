#!/usr/bin/env python3
"""
PORTED FROM PINHEAD-CLAUDE: Complete scoring and due factor calculations
These are the exact algorithms that produce the baseline results.
"""

import numpy as np
import pandas as pd
from utils import get_approximated_pa
import logging

logger = logging.getLogger(__name__)

# EXACT PINHEAD-CLAUDE CONSTANTS
DEFAULT_EXPECTED_H_PER_HR = 10.0
K_PA_THRESHOLD_FOR_LEAGUE_AVG = 30
K_PA_WARNING_THRESHOLD = 50

# EXACT PINHEAD-CLAUDE WEIGHTS
WEIGHTS = {
    'due_for_hr_factor': 0.5,         # AB-based due factor
    'due_for_hr_hits_factor': 0.3,    # Hits-based due factor
    'heating_up_contact_factor': 0.4, # Bonus if high contact, low recent HR
    'cold_batter_factor': 0.4,        # Penalty if very low recent contact
}

def calculate_recent_trends_exact_pinhead(games_performance):
    """
    PORTED FROM PINHEAD-CLAUDE: Exact calculate_recent_trends function
    Lines 44-124 from analyzer.py
    """
    if not games_performance:
        return {}
    
    num_games = len(games_performance)
    
    # Calculate totals across all games - EXACT PINHEAD-CLAUDE LOGIC
    total_ab = sum(g['AB'] for g in games_performance)
    total_h = sum(g['H'] for g in games_performance)
    total_hr = sum(g['HR'] for g in games_performance)
    total_bb = sum(g['BB'] for g in games_performance)
    total_k = sum(g['K'] for g in games_performance)
    total_pa_approx = sum(get_approximated_pa(g) for g in games_performance)
    
    # Calculate averages and rates - EXACT PINHEAD-CLAUDE LOGIC
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
    
    # Calculate trends (first half vs second half) - EXACT PINHEAD-CLAUDE LOGIC
    if num_games >= 2:
        mid_point = num_games // 2
        recent_half_games = games_performance[:mid_point]  # More recent games
        earlier_half_games = games_performance[mid_point:]  # Earlier games
        
        if recent_half_games and earlier_half_games:
            # HR/PA trend - EXACT PINHEAD-CLAUDE CALCULATION
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
            
            # Alternative trend: Contact quality - EXACT PINHEAD-CLAUDE CALCULATION
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

def calculate_recent_performance_bonus_exact_pinhead(recent_stats, player_type='hitter'):
    """
    PORTED FROM PINHEAD-CLAUDE: Exact calculate_recent_performance_bonus function
    Lines 212-250 from analyzer.py
    """
    if not recent_stats or recent_stats.get('total_games', 0) < 2:
        return 0
    
    bonus = 0
    
    if player_type == 'hitter':
        # Trend in HR rate - EXACT PINHEAD-CLAUDE LOGIC
        trend_magnitude_hr_rate = recent_stats.get('trend_magnitude', 0)
        if recent_stats.get('trend_direction') == 'improving':
            bonus += 15 * trend_magnitude_hr_rate * 100
        elif recent_stats.get('trend_direction') == 'declining':
            bonus -= 12 * trend_magnitude_hr_rate * 100
        
        # Recent HR rate level - EXACT PINHEAD-CLAUDE LOGIC
        hr_per_pa_recent = recent_stats.get('hr_per_pa', 0)
        if hr_per_pa_recent > 0.05:
            bonus += 20  # Strong recent HR rate
        elif hr_per_pa_recent > 0.03:
            bonus += 10
        elif hr_per_pa_recent < 0.01 and recent_stats.get('total_pa_approx', 0) > 20:
            bonus -= 10  # Very low recent HR rate
            
        # Hitting streak factor - EXACT PINHEAD-CLAUDE LOGIC
        avg_performance = recent_stats.get('avg_avg', 0)
        if avg_performance > 0.300:
            bonus += 15
        elif avg_performance > 0.275:
            bonus += 8
        elif avg_performance < 0.200 and recent_stats.get('total_ab', 0) > 10:
            bonus -= 12
            
        # Contact quality trend - EXACT PINHEAD-CLAUDE LOGIC
        hit_rate_trend = recent_stats.get('hit_rate_trend', {})
        if hit_rate_trend.get('direction') == 'improving' and hit_rate_trend.get('magnitude', 0) > 0.050:
            bonus += 10  # Significant improvement in contact quality
        
    return min(max(bonus, -30), 30)  # Cap bonus/penalty

def calculate_due_factors_exact_pinhead(batter_stats_2025_agg, stats_2024_hitter=None):
    """
    PORTED FROM PINHEAD-CLAUDE: Exact due factor calculations
    Lines 475-527 from enhanced_hr_likelihood_score function
    """
    due_factors = {
        'due_for_hr_ab_raw_score': 0,
        'due_for_hr_hits_raw_score': 0,
        'ab_since_last_hr': 0,
        'expected_ab_per_hr': 0,
        'h_since_last_hr': 0,
        'expected_h_per_hr': 0
    }
    
    if not batter_stats_2025_agg:
        return due_factors
    
    stats_2024_hitter = stats_2024_hitter or {}
    
    # 6b. Due for HR based on AB count - EXACT PINHEAD-CLAUDE LOGIC
    hr_2024_val = stats_2024_hitter.get('HR', 0)
    ab_2024_val = stats_2024_hitter.get('AB', 0)
    hr_2025_agg_val = batter_stats_2025_agg.get('HR', 0)
    ab_2025_agg_val = batter_stats_2025_agg.get('AB', 0)
    
    expected_hr_per_ab_val = 0
    if hr_2024_val > 0 and ab_2024_val >= 50:
        expected_hr_per_ab_val = hr_2024_val / ab_2024_val
    elif hr_2025_agg_val > 0 and ab_2025_agg_val >= 30:
        expected_hr_per_ab_val = hr_2025_agg_val / ab_2025_agg_val
    else:
        expected_hr_per_ab_val = 1 / 45.0  # Default expectation
    
    if expected_hr_per_ab_val > 0:
        ab_needed_for_hr_val = 1 / expected_hr_per_ab_val
        current_ab_since_hr_val = batter_stats_2025_agg.get('current_AB_since_last_HR', 0)
        
        due_factors.update({
            'ab_since_last_hr': current_ab_since_hr_val,
            'expected_ab_per_hr': round(ab_needed_for_hr_val, 1)
        })
        
        # EXACT PINHEAD-CLAUDE DUE CALCULATION
        if current_ab_since_hr_val > ab_needed_for_hr_val * 1.25:
            due_for_hr_ab_sub_score = min((current_ab_since_hr_val / ab_needed_for_hr_val - 1.25) * 20, 25)
            due_factors['due_for_hr_ab_raw_score'] = round(due_for_hr_ab_sub_score, 1)
    
    # 6c. Due for HR based on hits count - EXACT PINHEAD-CLAUDE LOGIC
    current_h_since_hr_val = batter_stats_2025_agg.get('current_H_since_last_HR', 0)
    expected_h_per_hr_from_stats = stats_2024_hitter.get('H_per_HR')
    
    if not pd.notna(expected_h_per_hr_from_stats) or expected_h_per_hr_from_stats <= 0:
        h_2025_agg = batter_stats_2025_agg.get('H', 0)
        hr_2025_agg = batter_stats_2025_agg.get('HR', 0)
        
        if hr_2025_agg > 0:
            expected_h_per_hr_from_stats = h_2025_agg / hr_2025_agg
        else:
            expected_h_per_hr_from_stats = DEFAULT_EXPECTED_H_PER_HR
    
    due_factors.update({
        'h_since_last_hr': current_h_since_hr_val,
        'expected_h_per_hr': round(expected_h_per_hr_from_stats, 1)
    })
    
    # EXACT PINHEAD-CLAUDE HITS DUE CALCULATION
    if expected_h_per_hr_from_stats > 0 and current_h_since_hr_val > expected_h_per_hr_from_stats * 1.5:
        due_for_hr_hits_sub_score = min(((current_h_since_hr_val / expected_h_per_hr_from_stats) - 1.5) * 15, 20)
        due_factors['due_for_hr_hits_raw_score'] = round(due_for_hr_hits_sub_score, 1)
    
    return due_factors

def calculate_contact_quality_factors_exact_pinhead(recent_stats, recent_batter_stats):
    """
    PORTED FROM PINHEAD-CLAUDE: Contact quality analysis for heating/cold factors
    """
    factors = {
        'heating_up_factor': 0,
        'cold_factor': 0,
        'contact_trend_description': 'N/A'
    }
    
    if not recent_stats or not recent_batter_stats:
        return factors
    
    # Get relevant metrics
    total_pa = recent_stats.get('total_pa_approx', 0)
    avg_avg = recent_stats.get('avg_avg', 0)
    hr_per_pa = recent_stats.get('hr_per_pa', 0)
    hit_rate_trend = recent_stats.get('hit_rate_trend', {})
    
    # Check for "heating up" - high contact, low recent power
    if (total_pa >= 20 and avg_avg > 0.275 and hr_per_pa < 0.02 and 
        hit_rate_trend.get('direction') == 'improving'):
        factors['heating_up_factor'] = 15
        factors['contact_trend_description'] = "Heating Up (High Contact, Low Recent Power)"
    
    # Check for "cold" - very low recent contact
    elif total_pa >= 15 and avg_avg < 0.200:
        factors['cold_factor'] = -20
        factors['contact_trend_description'] = "Cold Batter (Low Recent Contact)"
    
    return factors

def format_pinhead_baseline_compatible_result(api_result, recent_stats, due_factors, contact_factors):
    """
    Format API result to match exact Pinhead-Claude baseline output format
    """
    if not api_result:
        return api_result
    
    # Extract baseline-compatible values
    result = api_result.copy()
    
    # CRITICAL: Use exact Pinhead-Claude averaging method
    if recent_stats:
        # Use avg_avg from Pinhead-Claude calculation (average of individual game AVGs)
        result['recent_avg'] = recent_stats.get('avg_avg', 0)
        
        # Convert HR rate to decimal format (like baseline expects)
        hr_rate_decimal = recent_stats.get('hr_rate', 0)  # This is already AB-based decimal
        result['hr_rate'] = hr_rate_decimal
        
        # Recent trend direction from Pinhead-Claude calculation
        result['recent_trend_dir'] = recent_stats.get('trend_direction', 'stable')
        
        # Recent games count
        result['recent_games'] = recent_stats.get('total_games', 0)
    else:
        # Fallback values if no recent stats
        result['recent_avg'] = 0
        result['hr_rate'] = 0
        result['recent_trend_dir'] = 'stable'
        result['recent_games'] = 0
    
    # Add due factor scores
    if due_factors:
        result['ab_due'] = due_factors.get('due_for_hr_ab_raw_score', 0)
        result['h_due'] = due_factors.get('due_for_hr_hits_raw_score', 0)
    else:
        result['ab_due'] = 0
        result['h_due'] = 0
    
    # Add contact quality factors  
    if contact_factors:
        result['heating_up'] = contact_factors.get('heating_up_factor', 0)
        result['cold'] = contact_factors.get('cold_factor', 0)
        result['contact_trend'] = contact_factors.get('contact_trend_description', 'N/A')
    else:
        result['heating_up'] = 0
        result['cold'] = 0
        result['contact_trend'] = 'N/A'
    
    return result