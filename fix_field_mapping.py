#!/usr/bin/env python3
"""
Fix the field mapping issues for Recent Trend Dir and AB Due in API responses.

The issue:
1. UI expects: recent_N_games_raw_data.trends_summary_obj.trend_direction
   API returns: p_trend_dir (at top level)

2. UI expects: details.due_for_hr_ab_raw_score
   API returns: recent_N_games_raw_data.trends_summary_obj.ab_due

This script will show how to transform the response to match UI expectations.
"""

def transform_prediction_for_ui(prediction):
    """Transform API prediction to match UI expectations"""
    
    # Ensure we have the required nested structures
    if 'recent_N_games_raw_data' not in prediction:
        prediction['recent_N_games_raw_data'] = {}
    
    if 'trends_summary_obj' not in prediction['recent_N_games_raw_data']:
        prediction['recent_N_games_raw_data']['trends_summary_obj'] = {}
    
    if 'details' not in prediction:
        prediction['details'] = {}
    
    # 1. Fix Recent Trend Dir
    # Map p_trend_dir to the expected location
    if 'p_trend_dir' in prediction:
        prediction['recent_N_games_raw_data']['trends_summary_obj']['trend_direction'] = prediction['p_trend_dir']
        # Also add at top level for redundancy
        prediction['recent_trend_dir'] = prediction['p_trend_dir']
    
    # 2. Fix AB Due
    # Move ab_due from trends_summary_obj to details
    trends_obj = prediction['recent_N_games_raw_data']['trends_summary_obj']
    if 'ab_due' in trends_obj:
        prediction['details']['due_for_hr_ab_raw_score'] = trends_obj['ab_due']
        # Also add at top level for redundancy
        prediction['ab_due'] = trends_obj['ab_due']
    
    # 3. Add any other missing fields that the UI expects
    # Add default values if not present
    if 'trend_direction' not in prediction['recent_N_games_raw_data']['trends_summary_obj']:
        # Default to 'stable' if no trend data
        prediction['recent_N_games_raw_data']['trends_summary_obj']['trend_direction'] = 'stable'
        prediction['recent_trend_dir'] = 'stable'
    
    if 'due_for_hr_ab_raw_score' not in prediction['details']:
        # Default to 0 if no due factor
        prediction['details']['due_for_hr_ab_raw_score'] = 0
        prediction['ab_due'] = 0
    
    return prediction


# Example usage
if __name__ == "__main__":
    # Sample prediction from API
    sample_prediction = {
        "batter_name": "Cal Raleigh",
        "batter_team": "SEA",
        "p_trend_dir": "declining",  # This needs to be mapped
        "recent_N_games_raw_data": {
            "trends_summary_obj": {
                "ab_due": 15,  # This needs to be moved to details
                "avg_avg": 0.250,
                "hr_rate": 0.05
            }
        },
        "details": {
            "batter_pa_2025": 450,
            "overall_confidence": 0.75
        }
    }
    
    print("BEFORE transformation:")
    print(f"p_trend_dir: {sample_prediction.get('p_trend_dir')}")
    print(f"trends_summary_obj: {sample_prediction['recent_N_games_raw_data']['trends_summary_obj']}")
    print(f"details: {sample_prediction['details']}")
    
    # Transform
    transformed = transform_prediction_for_ui(sample_prediction.copy())
    
    print("\nAFTER transformation:")
    print(f"recent_trend_dir (top-level): {transformed.get('recent_trend_dir')}")
    print(f"trend_direction (in trends): {transformed['recent_N_games_raw_data']['trends_summary_obj'].get('trend_direction')}")
    print(f"ab_due (top-level): {transformed.get('ab_due')}")
    print(f"due_for_hr_ab_raw_score (in details): {transformed['details'].get('due_for_hr_ab_raw_score')}")