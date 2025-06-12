"""
Utilities for sorting prediction results by different criteria.
"""

def get_sort_key(prediction, sort_by='score'):
    """
    Get the appropriate sort key based on the sort criteria.
    Returns a function that extracts the requested value from a prediction.
    
    Parameters:
    -----------
    prediction : dict
        The prediction dictionary to extract value from
    sort_by : str
        The field to sort by (default: 'score')
        
    Returns:
    --------
    The value to use for sorting, or None if not available
    """
    # Always default to 0 for missing values to avoid errors
    if sort_by == 'score':
        return prediction.get('score', 0)
        
    # Outcome probabilities
    elif sort_by == 'hr' or sort_by == 'homerun':
        return prediction.get('outcome_probabilities', {}).get('homerun', 0)
    elif sort_by == 'hit':
        return prediction.get('outcome_probabilities', {}).get('hit', 0)
    elif sort_by == 'base' or sort_by == 'reach_base':
        return prediction.get('outcome_probabilities', {}).get('reach_base', 0)
    elif sort_by == 'k' or sort_by == 'strikeout':
        # For strikeout, lower is better for batters, so return negative value for proper sorting
        return -prediction.get('outcome_probabilities', {}).get('strikeout', 0)
        
    # Component scores
    elif sort_by == 'arsenal' or sort_by == 'arsenal_matchup':
        return prediction.get('matchup_components', {}).get('arsenal_matchup', 0)
    elif sort_by == 'batter' or sort_by == 'batter_overall':
        return prediction.get('matchup_components', {}).get('batter_overall', 0)
    elif sort_by == 'pitcher' or sort_by == 'pitcher_overall':
        return prediction.get('matchup_components', {}).get('pitcher_overall', 0)
    elif sort_by == 'historical' or sort_by == 'historical_yoy_csv':
        return prediction.get('matchup_components', {}).get('historical_yoy_csv', 0)
    elif sort_by == 'recent' or sort_by == 'recent_daily_games':
        return prediction.get('matchup_components', {}).get('recent_daily_games', 0)
    elif sort_by == 'contextual':
        return prediction.get('matchup_components', {}).get('contextual', 0)
        
    # Recent performance stats
    elif sort_by == 'recent_avg' or sort_by == 'avg':
        return prediction.get('recent_N_games_raw_data', {}).get('trends_summary_obj', {}).get('avg_avg', 0)
    elif sort_by == 'recent_hr_rate' or sort_by == 'hr_rate':
        return prediction.get('recent_N_games_raw_data', {}).get('trends_summary_obj', {}).get('hr_rate', 0)
    elif sort_by == 'recent_obp' or sort_by == 'obp':
        return prediction.get('recent_N_games_raw_data', {}).get('trends_summary_obj', {}).get('obp_calc', 0)
        
    # Due factors
    elif sort_by == 'due_ab' or sort_by == 'ab_due':
        return prediction.get('details', {}).get('due_for_hr_ab_raw_score', 0)
    elif sort_by == 'due_hits' or sort_by == 'hits_due':
        return prediction.get('details', {}).get('due_for_hr_hits_raw_score', 0)
    elif sort_by == 'contact_heat' or sort_by == 'heating_up':
        return prediction.get('details', {}).get('heating_up_contact_raw_score', 0)
    elif sort_by == 'cold':
        # For cold score, higher absolute values mean colder (more negative), so sort by negative value
        return -prediction.get('details', {}).get('cold_batter_contact_raw_score', 0)
        
    # Arsenal analysis metrics
    elif sort_by == 'hitter_slg':
        return prediction.get('details', {}).get('arsenal_analysis', {}).get('overall_summary_metrics', {}).get('hitter_avg_slg', 0)
    elif sort_by == 'pitcher_slg':
        return prediction.get('details', {}).get('arsenal_analysis', {}).get('overall_summary_metrics', {}).get('pitcher_avg_slg', 0)
        
    # Default to score if unknown sort key
    else:
        return prediction.get('score', 0)

def sort_predictions(predictions, sort_by='score', ascending=False):
    """
    Sort predictions by the specified criteria.
    
    Parameters:
    -----------
    predictions : list
        List of prediction dictionaries
    sort_by : str
        Field to sort by (default: 'score')
    ascending : bool
        Whether to sort in ascending order (default: False)
        
    Returns:
    --------
    list
        Sorted list of predictions
    """
    if not predictions:
        return []
        
    # Create a list of (prediction, sort_key) tuples
    # Use None as fallback for missing values, which will sort to the end
    predictions_with_keys = [(pred, get_sort_key(pred, sort_by)) for pred in predictions]
    
    # Sort by the extracted keys
    sorted_with_keys = sorted(predictions_with_keys, key=lambda x: x[1] or 0, reverse=not ascending)
    
    # Extract just the predictions from the sorted list
    return [pred for pred, _ in sorted_with_keys]

def get_sort_description(sort_by):
    """
    Get a human-readable description of the sort criteria.
    
    Parameters:
    -----------
    sort_by : str
        The field being sorted by
        
    Returns:
    --------
    str
        Description of the sort criteria
    """
    descriptions = {
        'score': 'Overall HR Score',
        'homerun': 'HR Probability',
        'hr': 'HR Probability',
        'hit': 'Hit Probability',
        'base': 'Reach Base Probability',
        'reach_base': 'Reach Base Probability',
        'k': 'Strikeout Probability (lowest first)',
        'strikeout': 'Strikeout Probability (lowest first)',
        'arsenal': 'Arsenal Matchup Component',
        'arsenal_matchup': 'Arsenal Matchup Component',
        'batter': 'Batter Overall Component',
        'batter_overall': 'Batter Overall Component',
        'pitcher': 'Pitcher Overall Component',
        'pitcher_overall': 'Pitcher Overall Component',
        'historical': 'Historical Trend Component',
        'historical_yoy_csv': 'Historical Trend Component',
        'recent': 'Recent Performance Component',
        'recent_daily_games': 'Recent Performance Component',
        'contextual': 'Contextual Factors Component',
        'recent_avg': 'Recent Batting Average',
        'avg': 'Recent Batting Average',
        'recent_hr_rate': 'Recent HR Rate',
        'hr_rate': 'Recent HR Rate',
        'recent_obp': 'Recent On-Base Percentage',
        'obp': 'Recent On-Base Percentage',
        'due_ab': 'Due for HR (AB-based)',
        'ab_due': 'Due for HR (AB-based)',
        'due_hits': 'Due for HR (hits-based)',
        'hits_due': 'Due for HR (hits-based)',
        'contact_heat': 'Heating Up Contact Score',
        'heating_up': 'Heating Up Contact Score',
        'cold': 'Cold Batter Score',
        'hitter_slg': 'Hitter SLG vs Arsenal',
        'pitcher_slg': 'Pitcher SLG Allowed'
    }
    
    return descriptions.get(sort_by, f"Custom Sort ({sort_by})")