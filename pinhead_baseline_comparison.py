#!/usr/bin/env python3
"""
Compare Pinhead-Claude baseline results with PinheadsPlayhouse API results
to identify discrepancies and verify data accuracy.
"""

import requests
import json
import pandas as pd
from datetime import datetime

API_BASE_URL = "http://127.0.0.1:8000"
BASELINE_CSV = "/Users/futurepr0n/Development/Capping.Pro/Claude-Code/Pinhead-Claude/combined_analysis_enhanced_20250626_091605.csv"

def load_baseline_data():
    """Load the Pinhead-Claude baseline results"""
    print("📊 Loading Pinhead-Claude baseline data...")
    
    try:
        df = pd.read_csv(BASELINE_CSV)
        print(f"✅ Loaded {len(df)} baseline predictions")
        return df
    except Exception as e:
        print(f"❌ Error loading baseline data: {e}")
        return None

def get_api_results(pitcher_name, team_abbr):
    """Get results from PinheadsPlayhouse API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/analyze/pitcher-vs-team",
            json={
                "pitcher_name": pitcher_name,
                "team": team_abbr,
                "sort_by": "score",
                "min_score": 0,
                "include_confidence_metrics": True
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"❌ API Error for {pitcher_name} vs {team_abbr}: {e}")
        return None

def compare_predictions():
    """Compare baseline vs API results for key matchups"""
    
    print("🔍 PINHEAD-CLAUDE vs PINHEADSPLAYHOUSE COMPARISON")
    print("=" * 80)
    
    # Load baseline data
    baseline_df = load_baseline_data()
    if baseline_df is None:
        return
    
    # Extract unique pitcher-team combinations from baseline
    baseline_matchups = baseline_df.groupby(['Pitcher', 'Batter_Team']).first().reset_index()
    
    print(f"📈 Found {len(baseline_matchups)} unique pitcher-team matchups in baseline")
    
    # Test a subset of matchups (first 5 for detailed comparison)
    test_matchups = baseline_matchups.head(5)
    
    comparison_results = []
    
    for idx, matchup in test_matchups.iterrows():
        pitcher = matchup['Pitcher']
        team = matchup['Batter_Team']
        
        print(f"\n🎯 COMPARING: {pitcher} vs {team}")
        print("-" * 60)
        
        # Get baseline players for this matchup
        baseline_players = baseline_df[
            (baseline_df['Pitcher'] == pitcher) & 
            (baseline_df['Batter_Team'] == team)
        ].copy()
        
        # Get API results
        api_data = get_api_results(pitcher, team)
        
        if api_data and api_data.get('success'):
            api_predictions = api_data.get('predictions', [])
            print(f"✅ API returned {len(api_predictions)} predictions")
            print(f"📊 Baseline has {len(baseline_players)} predictions")
            
            # Compare individual players
            comparison = compare_player_data(baseline_players, api_predictions, pitcher, team)
            comparison_results.append(comparison)
        else:
            print(f"❌ API failed for {pitcher} vs {team}")
    
    # Generate summary report
    generate_comparison_report(comparison_results)

def compare_player_data(baseline_players, api_predictions, pitcher, team):
    """Compare individual player data between baseline and API"""
    
    comparison = {
        'pitcher': pitcher,
        'team': team,
        'baseline_count': len(baseline_players),
        'api_count': len(api_predictions),
        'player_matches': [],
        'field_comparisons': {},
        'discrepancies': []
    }
    
    # Key fields to compare
    comparison_fields = {
        # Baseline field -> API field mapping
        'Recent_AVG': 'recent_avg',
        'Recent_HR_Rate': 'hr_rate', 
        'Recent_Trend_Dir': 'recent_trend_dir',
        'Pitcher_Trend_Dir': 'p_trend_dir',
        'Pitcher_Recent_ERA': 'p_recent_era',
        'HR_Score': 'score',
        'AB_Due_Score': 'ab_due',
        'H_Due_Score': 'h_due',
        'Recent_Games': 'recent_games'
    }
    
    # Create player name mapping for comparison
    baseline_players_dict = {}
    for _, player in baseline_players.iterrows():
        # Clean player name for matching
        clean_name = clean_player_name(player['Batter'])
        baseline_players_dict[clean_name] = player
    
    api_players_dict = {}
    for pred in api_predictions:
        clean_name = clean_player_name(pred.get('batter_name', ''))
        api_players_dict[clean_name] = pred
    
    # Find matching players
    baseline_names = set(baseline_players_dict.keys())
    api_names = set(api_players_dict.keys())
    
    matched_names = baseline_names.intersection(api_names)
    baseline_only = baseline_names - api_names
    api_only = api_names - baseline_names
    
    print(f"👥 Player Matching:")
    print(f"   Matched: {len(matched_names)}")
    print(f"   Baseline only: {len(baseline_only)} {list(baseline_only)[:3]}")
    print(f"   API only: {len(api_only)} {list(api_only)[:3]}")
    
    # Compare matched players
    for name in matched_names:
        baseline_player = baseline_players_dict[name]
        api_player = api_players_dict[name]
        
        player_comparison = compare_player_fields(
            baseline_player, api_player, comparison_fields, name
        )
        comparison['player_matches'].append(player_comparison)
    
    return comparison

def clean_player_name(name):
    """Clean player name for matching"""
    if not name:
        return ""
    
    # Remove common variations
    cleaned = name.strip()
    cleaned = cleaned.replace("JR", "").replace("Jr", "").replace("Jr.", "")
    cleaned = cleaned.replace("III", "").replace("II", "")
    cleaned = " ".join(cleaned.split())  # Remove extra spaces
    
    return cleaned.lower()

def compare_player_fields(baseline_player, api_player, field_mapping, player_name):
    """Compare specific fields for a player"""
    
    player_comp = {
        'name': player_name,
        'field_matches': {},
        'significant_differences': []
    }
    
    for baseline_field, api_field in field_mapping.items():
        baseline_value = get_field_value(baseline_player, baseline_field)
        api_value = get_nested_api_value(api_player, api_field)
        
        # Compare values
        match_result = compare_field_values(baseline_value, api_value, baseline_field)
        player_comp['field_matches'][baseline_field] = match_result
        
        if not match_result['matches']:
            player_comp['significant_differences'].append({
                'field': baseline_field,
                'baseline': baseline_value,
                'api': api_value,
                'difference': match_result.get('difference', 'N/A')
            })
    
    return player_comp

def get_field_value(player_data, field):
    """Get field value from baseline data"""
    if hasattr(player_data, field):
        return getattr(player_data, field)
    elif field in player_data:
        return player_data[field]
    else:
        return None

def get_nested_api_value(api_data, field_path):
    """Get nested field value from API data"""
    
    # Direct field access
    if field_path in api_data:
        return api_data[field_path]
    
    # Try nested structures
    nested_paths = {
        'recent_avg': ['recent_N_games_raw_data', 'trends_summary_obj', 'avg_avg'],
        'hr_rate': ['recent_N_games_raw_data', 'trends_summary_obj', 'hr_rate'],
        'recent_trend_dir': ['recent_N_games_raw_data', 'trends_summary_obj', 'trend_direction'],
        'ab_due': ['details', 'due_for_hr_ab_raw_score']
    }
    
    if field_path in nested_paths:
        current = api_data
        for key in nested_paths[field_path]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    
    return None

def compare_field_values(baseline_val, api_val, field_name):
    """Compare two field values"""
    
    result = {
        'matches': False,
        'baseline': baseline_val,
        'api': api_val,
        'difference': None
    }
    
    # Handle None values
    if baseline_val is None and api_val is None:
        result['matches'] = True
        return result
    
    if baseline_val is None or api_val is None:
        result['difference'] = 'One value is None'
        return result
    
    # Handle numeric comparisons
    if isinstance(baseline_val, (int, float)) and isinstance(api_val, (int, float)):
        diff = abs(baseline_val - api_val)
        tolerance = 0.001  # Small tolerance for floating point
        
        if diff <= tolerance:
            result['matches'] = True
        else:
            result['difference'] = diff
        return result
    
    # Handle string comparisons
    if isinstance(baseline_val, str) and isinstance(api_val, str):
        if baseline_val.lower().strip() == api_val.lower().strip():
            result['matches'] = True
        else:
            result['difference'] = f"'{baseline_val}' vs '{api_val}'"
        return result
    
    # Type mismatch
    result['difference'] = f"Type mismatch: {type(baseline_val)} vs {type(api_val)}"
    return result

def generate_comparison_report(comparison_results):
    """Generate comprehensive comparison report"""
    
    print("\n" + "=" * 80)
    print("📊 PINHEAD-CLAUDE vs PINHEADSPLAYHOUSE COMPARISON REPORT")
    print("=" * 80)
    
    if not comparison_results:
        print("❌ No comparison results available")
        return
    
    # Overall statistics
    total_matchups = len(comparison_results)
    total_players_baseline = sum(comp['baseline_count'] for comp in comparison_results)
    total_players_api = sum(comp['api_count'] for comp in comparison_results)
    
    print(f"\n📈 OVERALL STATISTICS")
    print(f"Matchups tested: {total_matchups}")
    print(f"Total baseline players: {total_players_baseline}")
    print(f"Total API players: {total_players_api}")
    
    # Field accuracy analysis
    print(f"\n📋 FIELD ACCURACY ANALYSIS")
    
    field_stats = {}
    total_matches = 0
    
    for comp in comparison_results:
        for player_match in comp['player_matches']:
            total_matches += 1
            for field, match_result in player_match['field_matches'].items():
                if field not in field_stats:
                    field_stats[field] = {'matches': 0, 'total': 0, 'sample_diffs': []}
                
                field_stats[field]['total'] += 1
                if match_result['matches']:
                    field_stats[field]['matches'] += 1
                else:
                    if len(field_stats[field]['sample_diffs']) < 3:
                        field_stats[field]['sample_diffs'].append({
                            'baseline': match_result['baseline'],
                            'api': match_result['api'],
                            'diff': match_result.get('difference', 'Unknown')
                        })
    
    for field, stats in sorted(field_stats.items()):
        if stats['total'] > 0:
            accuracy = (stats['matches'] / stats['total']) * 100
            print(f"{field:20} - {accuracy:5.1f}% match rate ({stats['matches']}/{stats['total']})")
            
            if stats['sample_diffs']:
                print(f"{'':22} Sample differences:")
                for diff in stats['sample_diffs'][:2]:
                    print(f"{'':24} Baseline: {diff['baseline']} | API: {diff['api']}")
    
    # Critical discrepancies
    print(f"\n⚠️ CRITICAL DISCREPANCIES")
    
    critical_fields = ['Recent_AVG', 'Recent_Trend_Dir', 'Pitcher_Trend_Dir', 'HR_Score']
    
    for comp in comparison_results:
        pitcher_team = f"{comp['pitcher']} vs {comp['team']}"
        
        for player_match in comp['player_matches']:
            critical_diffs = [
                diff for diff in player_match['significant_differences'] 
                if diff['field'] in critical_fields
            ]
            
            if critical_diffs:
                print(f"\n🔍 {pitcher_team} - {player_match['name']}:")
                for diff in critical_diffs:
                    print(f"   {diff['field']}: Baseline={diff['baseline']} | API={diff['api']}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"/Users/futurepr0n/Development/Capping.Pro/Claude-Code/BaseballAPI/baseline_comparison_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(comparison_results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed comparison saved to: {output_file}")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    compare_predictions()