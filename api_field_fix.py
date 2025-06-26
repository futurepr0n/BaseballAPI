#!/usr/bin/env python3
"""
Patch for enhanced_main.py to fix field mapping issues.
This adds the transform_prediction_for_ui function to properly map fields.
"""

# Add this function to enhanced_main.py after the imports

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
    
    # 4. Ensure other expected fields exist with proper defaults
    # Add hits_due if present in trends
    if 'hits_due' in trends_obj:
        prediction['details']['due_for_hr_hits_raw_score'] = trends_obj.get('hits_due', 0)
        prediction['hits_due'] = trends_obj.get('hits_due', 0)
    
    return prediction


# Instructions to apply this fix:
# 1. Add the transform_prediction_for_ui function to enhanced_main.py after the imports
# 2. In the /analyze/pitcher-vs-team endpoint, after getting the result, transform predictions:
#    if result.get('predictions'):
#        result['predictions'] = [transform_prediction_for_ui(pred) for pred in result['predictions']]
# 3. In the /analyze/batch endpoint, do the same transformation for all predictions
# 4. In any other endpoints that return predictions, apply the same transformation

print("""
PATCH INSTRUCTIONS:

1. Copy the transform_prediction_for_ui function into enhanced_main.py

2. Find the /analyze/pitcher-vs-team endpoint and add after the analysis:
   # Transform predictions to match UI expectations
   if result.get('predictions'):
       result['predictions'] = [transform_prediction_for_ui(pred) for pred in result['predictions']]

3. Find the /analyze/batch endpoint and add similar transformation

4. Restart the API

This will ensure Recent Trend Dir and AB Due show correct values in PinheadsPlayhouse.
""")