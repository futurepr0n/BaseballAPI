"""
Utilities for filtering prediction results based on various criteria.
"""

def filter_predictions(predictions, filter_criteria=None):
    """
    Filter predictions based on specified criteria.
    
    Parameters:
    -----------
    predictions : list
        List of prediction dictionaries
    filter_criteria : dict
        Dictionary of filter criteria with values
        
    Returns:
    --------
    list
        Filtered list of predictions
    """
    if not predictions or not filter_criteria:
        return predictions
        
    filtered_predictions = predictions.copy()
    
    # Apply trend filters
    if 'trend' in filter_criteria:
        trend_filter = filter_criteria['trend'].lower()
        if trend_filter in ['improving', 'declining', 'stable']:
            # Historical metrics trends
            if 'historical' in trend_filter or 'all' in trend_filter:
                filtered_predictions = [
                    pred for pred in filtered_predictions
                    if has_historical_trend_direction(pred, trend_filter)
                ]
            
            # Recent performance trend
            if 'recent' in trend_filter or 'all' in trend_filter:
                filtered_predictions = [
                    pred for pred in filtered_predictions
                    if has_recent_trend_direction(pred, trend_filter)
                ]
            
            # If just the trend is specified without qualifier, check both
            if trend_filter in ['improving', 'declining', 'stable']:
                filtered_predictions = [
                    pred for pred in filtered_predictions
                    if has_historical_trend_direction(pred, trend_filter) or 
                    has_recent_trend_direction(pred, trend_filter)
                ]
    
    # Filter by minimum threshold values
    if 'min_score' in filter_criteria:
        min_score = float(filter_criteria['min_score'])
        filtered_predictions = [pred for pred in filtered_predictions if pred.get('score', 0) >= min_score]
    
    if 'min_hr_prob' in filter_criteria:
        min_hr_prob = float(filter_criteria['min_hr_prob'])
        filtered_predictions = [
            pred for pred in filtered_predictions 
            if pred.get('outcome_probabilities', {}).get('homerun', 0) >= min_hr_prob
        ]
    
    if 'min_hit_prob' in filter_criteria:
        min_hit_prob = float(filter_criteria['min_hit_prob'])
        filtered_predictions = [
            pred for pred in filtered_predictions 
            if pred.get('outcome_probabilities', {}).get('hit', 0) >= min_hit_prob
        ]
    
    if 'max_k_prob' in filter_criteria:
        max_k_prob = float(filter_criteria['max_k_prob'])
        filtered_predictions = [
            pred for pred in filtered_predictions 
            if pred.get('outcome_probabilities', {}).get('strikeout', 0) <= max_k_prob
        ]
    
    # Filter by contact quality
    if 'contact_trend' in filter_criteria:
        contact_filter = filter_criteria['contact_trend'].lower()
        if contact_filter == 'heating':
            filtered_predictions = [
                pred for pred in filtered_predictions
                if pred.get('details', {}).get('contact_trend', '').lower().startswith('heating')
            ]
        elif contact_filter == 'cold':
            filtered_predictions = [
                pred for pred in filtered_predictions
                if pred.get('details', {}).get('contact_trend', '').lower().startswith('cold')
            ]
    
    # Filter by due factors
    if 'min_due_ab' in filter_criteria:
        min_due_ab = float(filter_criteria['min_due_ab'])
        filtered_predictions = [
            pred for pred in filtered_predictions
            if pred.get('details', {}).get('due_for_hr_ab_raw_score', 0) >= min_due_ab
        ]
    
    if 'min_due_hits' in filter_criteria:
        min_due_hits = float(filter_criteria['min_due_hits'])
        filtered_predictions = [
            pred for pred in filtered_predictions
            if pred.get('details', {}).get('due_for_hr_hits_raw_score', 0) >= min_due_hits
        ]
    
    return filtered_predictions

def has_historical_trend_direction(prediction, trend_direction):
    """
    Check if a prediction has the specified historical trend direction.
    
    Parameters:
    -----------
    prediction : dict
        The prediction dictionary
    trend_direction : str
        The trend direction to check for ('improving', 'declining', 'stable')
        
    Returns:
    --------
    bool
        True if any historical metrics have the specified trend, False otherwise
    """
    historical_metrics = prediction.get('details', {}).get('historical_metrics', [])
    
    if not historical_metrics:
        return False
        
    # Check if any metrics have the specified trend direction
    for metric in historical_metrics:
        if metric.get('direction', '').lower() == trend_direction.lower():
            return True
            
    return False

def has_recent_trend_direction(prediction, trend_direction):
    """
    Check if a prediction has the specified recent performance trend direction.
    
    Parameters:
    -----------
    prediction : dict
        The prediction dictionary
    trend_direction : str
        The trend direction to check for ('improving', 'declining', 'stable')
        
    Returns:
    --------
    bool
        True if recent trend has the specified direction, False otherwise
    """
    recent_data = prediction.get('recent_N_games_raw_data', {})
    trend_obj = recent_data.get('trends_summary_obj', {})
    
    trend_dir = trend_obj.get('trend_direction', '')
    
    return trend_dir.lower() == trend_direction.lower()

def print_filter_options():
    """Print all available filtering options for the user."""
    print("\nAvailable Filtering Options:")
    print("===========================")
    
    print("\nTrend Filters:")
    print("  --filter-trend=improving     : Only players with improving metrics")
    print("  --filter-trend=declining     : Only players with declining metrics")
    print("  --filter-trend=stable        : Only players with stable metrics")
    
    print("\nMinimum Threshold Filters:")
    print("  --filter-min-score=50        : Only players with score ≥ 50")
    print("  --filter-min-hr-prob=10      : Only players with HR probability ≥ 10%")
    print("  --filter-min-hit-prob=30     : Only players with hit probability ≥ 30%")
    print("  --filter-max-k-prob=40       : Only players with strikeout probability ≤ 40%")
    
    print("\nContact Quality Filters:")
    print("  --filter-contact=heating     : Only players heating up (high contact, low HR)")
    print("  --filter-contact=cold        : Only players in a cold streak")
    
    print("\nDue Factor Filters:")
    print("  --filter-min-due-ab=10       : Only players with AB-based due score ≥ 10")
    print("  --filter-min-due-hits=5      : Only players with hits-based due score ≥ 5")
    
    print("\nExamples:")
    print("  python main.py --filter-trend=improving \"Sean Burke\" TEX")
    print("  python main.py --filter-min-hr-prob=15 --filter-max-k-prob=35 \"MacKenzie Gore\" SEA")
    print("  python main.py --filter-contact=heating --sort=recent_avg \"Justin Verlander\" LAD")
    print("  python main.py --filter-trend=improving --filter-min-due-ab=8 --batch=matchups.txt")

if __name__ == "__main__":
    print_filter_options()