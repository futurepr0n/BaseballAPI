#!/usr/bin/env python3
"""
Comprehensive analysis test to validate ALL columns and data flow scenarios:
1. Batch analysis (multiple teams) 
2. Single team analysis
3. FALLBACK vs non-FALLBACK scenarios
4. ALL possible column validation
5. Consistency checks for pitcher data across hitters
"""

import requests
import json
from datetime import datetime

API_BASE_URL = "http://127.0.0.1:8000"

def test_comprehensive_analysis():
    """Run comprehensive tests across all scenarios"""
    
    print("🧪 COMPREHENSIVE BASEBALL API ANALYSIS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Test scenarios
    scenarios = [
        # High data scenarios (established pitchers)
        {"pitcher": "Max Fried", "teams": ["CHC"], "expected_data": "high"},
        {"pitcher": "Spencer Strider", "teams": ["ATL"], "expected_data": "high"},
        {"pitcher": "Sandy Alcantara", "teams": ["MIA"], "expected_data": "high"},
        
        # Mixed data scenarios  
        {"pitcher": "Max Fried", "teams": ["CHC", "CIN", "ARI"], "expected_data": "mixed"},
        
        # Fallback scenarios (unknown/new pitchers)
        {"pitcher": "Unknown Pitcher", "teams": ["CHC"], "expected_data": "fallback"},
        {"pitcher": "John Smith", "teams": ["ATL"], "expected_data": "fallback"},
    ]
    
    all_results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📊 SCENARIO {i}: {scenario['pitcher']} vs {scenario['teams']}")
        print("-" * 60)
        
        for team in scenario['teams']:
            print(f"\n🎯 Testing: {scenario['pitcher']} vs {team}")
            
            # Make API request
            try:
                response = requests.post(
                    f"{API_BASE_URL}/analyze/pitcher-vs-team",
                    json={
                        "pitcher_name": scenario['pitcher'],
                        "team_abbr": team,
                        "sort_by": "score",
                        "min_score": 0,
                        "include_confidence_metrics": True
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = analyze_response_data(scenario['pitcher'], team, data, scenario['expected_data'])
                    all_results.append(result)
                else:
                    print(f"❌ API Error: {response.status_code} - {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Request Error: {e}")
    
    # Generate comprehensive report
    generate_comprehensive_report(all_results)

def analyze_response_data(pitcher_name, team, response_data, expected_data_level):
    """Analyze a single API response for all possible columns"""
    
    analysis = {
        'pitcher': pitcher_name,
        'team': team,
        'expected_data_level': expected_data_level,
        'timestamp': datetime.now().isoformat(),
        'success': response_data.get('success', False),
        'predictions_count': len(response_data.get('predictions', [])),
        'columns_analysis': {},
        'consistency_checks': {},
        'data_quality': {}
    }
    
    if not response_data.get('success'):
        analysis['error'] = response_data.get('error', 'Unknown error')
        return analysis
    
    predictions = response_data.get('predictions', [])
    if not predictions:
        analysis['error'] = 'No predictions returned'
        return analysis
    
    print(f"✅ Success: {len(predictions)} predictions returned")
    
    # Analyze ALL possible columns
    all_columns = [
        # Core scoring
        'score', 'confidence', 'data_source',
        
        # Recent performance  
        'recent_avg', 'hr_rate', 'recent_trend_dir',
        
        # Pitcher data (should be consistent across hitters)
        'p_trend_dir', 'p_recent_era', 'p_early_era', 'p_games_analyzed',
        
        # Component scores
        'component_breakdown', 'outcome_probabilities',
        
        # Detailed fields
        'ab_due', 'recent_N_games_raw_data', 'details',
        
        # Player info
        'batter_name', 'batter_team', 'pitcher_name', 'pitcher_team',
        'batter_hand', 'pitcher_hand'
    ]
    
    # Analyze each column
    for column in all_columns:
        analysis['columns_analysis'][column] = analyze_column_data(predictions, column)
    
    # Consistency checks (pitcher data should be identical across hitters)
    pitcher_consistency_fields = ['p_trend_dir', 'p_recent_era', 'p_early_era', 'pitcher_name', 'pitcher_team']
    analysis['consistency_checks'] = check_pitcher_consistency(predictions, pitcher_consistency_fields)
    
    # Data quality assessment
    analysis['data_quality'] = assess_data_quality(predictions, expected_data_level)
    
    return analysis

def analyze_column_data(predictions, column):
    """Analyze a specific column across all predictions"""
    
    column_data = {
        'present_count': 0,
        'missing_count': 0,
        'unique_values': set(),
        'data_types': set(),
        'sample_values': [],
        'has_fallback_indicators': False
    }
    
    for pred in predictions:
        # Handle nested fields
        value = get_nested_field(pred, column)
        
        if value is not None and value != 0 and value != '':
            column_data['present_count'] += 1
            column_data['unique_values'].add(str(value)[:50])  # Truncate long values
            column_data['data_types'].add(type(value).__name__)
            
            if len(column_data['sample_values']) < 3:
                column_data['sample_values'].append(value)
                
            # Check for fallback indicators
            if isinstance(value, str) and ('fallback' in value.lower() or 'league' in value.lower()):
                column_data['has_fallback_indicators'] = True
                
        else:
            column_data['missing_count'] += 1
    
    # Convert sets to lists for JSON serialization
    column_data['unique_values'] = list(column_data['unique_values'])
    column_data['data_types'] = list(column_data['data_types'])
    
    return column_data

def get_nested_field(data, field_path):
    """Get a nested field value, handling various structures"""
    
    # Direct field access
    if field_path in data:
        return data[field_path]
    
    # Nested structure access
    nested_paths = {
        'ab_due': ['recent_N_games_raw_data', 'trends_summary_obj', 'ab_due'],
        'trend_direction': ['recent_N_games_raw_data', 'trends_summary_obj', 'trend_direction'],
        'due_for_hr_ab': ['details', 'due_for_hr_ab_raw_score']
    }
    
    if field_path in nested_paths:
        current = data
        for key in nested_paths[field_path]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    
    return None

def check_pitcher_consistency(predictions, consistency_fields):
    """Check if pitcher-related fields are consistent across all hitters"""
    
    consistency_results = {}
    
    for field in consistency_fields:
        values = []
        for pred in predictions:
            value = get_nested_field(pred, field)
            if value is not None:
                values.append(value)
        
        consistency_results[field] = {
            'unique_values': list(set(values)),
            'is_consistent': len(set(values)) <= 1,
            'total_values': len(values),
            'sample_value': values[0] if values else None
        }
    
    return consistency_results

def assess_data_quality(predictions, expected_level):
    """Assess overall data quality"""
    
    quality_metrics = {
        'expected_level': expected_level,
        'fallback_count': 0,
        'non_fallback_count': 0,
        'missing_critical_fields': [],
        'data_completeness_score': 0
    }
    
    critical_fields = ['recent_avg', 'hr_rate', 'score', 'confidence']
    
    total_critical_present = 0
    total_critical_possible = len(predictions) * len(critical_fields)
    
    for pred in predictions:
        # Check for fallback indicators
        data_source = pred.get('data_source', '')
        if 'fallback' in data_source.lower() or 'league' in data_source.lower():
            quality_metrics['fallback_count'] += 1
        else:
            quality_metrics['non_fallback_count'] += 1
        
        # Check critical fields
        for field in critical_fields:
            value = get_nested_field(pred, field)
            if value is not None and value != 0:
                total_critical_present += 1
            elif field not in quality_metrics['missing_critical_fields']:
                quality_metrics['missing_critical_fields'].append(field)
    
    quality_metrics['data_completeness_score'] = (total_critical_present / total_critical_possible) * 100 if total_critical_possible > 0 else 0
    
    return quality_metrics

def generate_comprehensive_report(all_results):
    """Generate a comprehensive analysis report"""
    
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE ANALYSIS REPORT")
    print("=" * 80)
    
    # Summary statistics
    total_tests = len(all_results)
    successful_tests = sum(1 for r in all_results if r.get('success', False))
    
    print(f"\n📈 SUMMARY STATISTICS")
    print(f"Total tests run: {total_tests}")
    print(f"Successful tests: {successful_tests}")
    print(f"Success rate: {(successful_tests/total_tests)*100:.1f}%")
    
    # Column completeness analysis
    print(f"\n📋 COLUMN COMPLETENESS ANALYSIS")
    column_summary = {}
    
    for result in all_results:
        if result.get('success'):
            for column, data in result.get('columns_analysis', {}).items():
                if column not in column_summary:
                    column_summary[column] = {'total_present': 0, 'total_tests': 0, 'fallback_indicators': 0}
                
                column_summary[column]['total_present'] += data.get('present_count', 0)
                column_summary[column]['total_tests'] += data.get('present_count', 0) + data.get('missing_count', 0)
                if data.get('has_fallback_indicators'):
                    column_summary[column]['fallback_indicators'] += 1
    
    for column, stats in sorted(column_summary.items()):
        if stats['total_tests'] > 0:
            completeness = (stats['total_present'] / stats['total_tests']) * 100
            print(f"{column:20} - {completeness:5.1f}% complete ({stats['total_present']}/{stats['total_tests']})")
    
    # Consistency analysis
    print(f"\n🔄 PITCHER CONSISTENCY ANALYSIS")
    consistency_issues = []
    
    for result in all_results:
        if result.get('success'):
            pitcher = result.get('pitcher')
            team = result.get('team')
            
            for field, consistency in result.get('consistency_checks', {}).items():
                if not consistency.get('is_consistent'):
                    consistency_issues.append({
                        'pitcher': pitcher,
                        'team': team,
                        'field': field,
                        'unique_values': consistency.get('unique_values', [])
                    })
    
    if consistency_issues:
        print("❌ CONSISTENCY ISSUES FOUND:")
        for issue in consistency_issues:
            print(f"  {issue['pitcher']} vs {issue['team']}: {issue['field']} has multiple values: {issue['unique_values']}")
    else:
        print("✅ All pitcher data is consistent across hitters")
    
    # Data quality by scenario
    print(f"\n📊 DATA QUALITY BY SCENARIO")
    
    fallback_scenarios = [r for r in all_results if r.get('expected_data_level') == 'fallback']
    high_data_scenarios = [r for r in all_results if r.get('expected_data_level') == 'high']
    
    if fallback_scenarios:
        avg_fallback_score = sum(r.get('data_quality', {}).get('data_completeness_score', 0) for r in fallback_scenarios) / len(fallback_scenarios)
        print(f"Fallback scenarios avg completeness: {avg_fallback_score:.1f}%")
    
    if high_data_scenarios:
        avg_high_score = sum(r.get('data_quality', {}).get('data_completeness_score', 0) for r in high_data_scenarios) / len(high_data_scenarios)
        print(f"High-data scenarios avg completeness: {avg_high_score:.1f}%")
    
    # Save detailed results
    with open('/Users/futurepr0n/Development/Capping.Pro/Claude-Code/BaseballAPI/comprehensive_analysis_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: comprehensive_analysis_results.json")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_comprehensive_analysis()