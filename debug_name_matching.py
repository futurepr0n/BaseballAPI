#!/usr/bin/env python3
"""
Debug script to analyze the name matching issue in BaseballAPI
"""

import json
import os

def analyze_name_matching_issue():
    """Analyze the exact name matching problem"""
    print("🔍 DEBUGGING NAME MATCHING ISSUE")
    print("="*50)
    
    # Example problematic case
    test_cases = [
        {
            "requested_name": "Aramis Garcia",  # From PinheadsPlayhouse
            "roster_name": "A. Garcia",         # From rosters.json name field
            "roster_fullname": "Aramis Garcia", # From rosters.json fullName field
            "daily_json_name": "A. Garcia",     # From daily JSON files
            "expected_flow": "Aramis Garcia → A. Garcia → Find in daily files"
        },
        {
            "requested_name": "Angel Martinez", 
            "roster_name": "A. Martinez",
            "roster_fullname": "Angel Martinez",
            "daily_json_name": "A. Martinez",
            "expected_flow": "Angel Martinez → A. Martinez → Find in daily files"
        }
    ]
    
    print("📋 TEST CASES:")
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. {case['requested_name']}:")
        print(f"   Roster name field: '{case['roster_name']}'")
        print(f"   Roster fullName:   '{case['roster_fullname']}'")
        print(f"   Daily JSON name:   '{case['daily_json_name']}'")
        print(f"   Expected flow:     {case['expected_flow']}")
    
    print("\n🔧 CURRENT LOOKUP PROCESS:")
    print("1. PinheadsPlayhouse sends: 'Aramis Garcia'")
    print("2. get_last_n_games_performance(player_full_name_resolved='Aramis Garcia', ...)")
    print("3. Line 505: Look for fullName_cleaned == 'Aramis Garcia' in roster")
    print("4. Line 506: Get the 'name' field → 'A. Garcia'")
    print("5. Search daily files for 'A. Garcia'")
    print("6. Daily files have 'A. Garcia' → Should work!")
    
    print("\n❌ WHERE IT'S FAILING:")
    print("The issue is likely in:")
    print("• clean_player_name() function changing 'A. Garcia' to 'A Garcia'")
    print("• match_player_name_to_roster() fuzzy matching logic")
    print("• Case sensitivity or whitespace issues")
    print("• Team matching failures")
    
    print("\n🎯 THE REAL CULPRIT:")
    print("After roster cleanup:")
    print("• We have fullName: 'Aramis Garcia' (corrected)")
    print("• But name: 'A. Garcia' (unchanged)")
    print("• Daily files still use: 'A. Garcia'")
    print("• The lookup chain should work, but there's a bug in the matching logic")
    
    return analyze_specific_functions()

def analyze_specific_functions():
    """Analyze the specific functions causing issues"""
    print("\n🔍 FUNCTION-SPECIFIC ANALYSIS:")
    print("="*40)
    
    functions_to_fix = {
        "get_last_n_games_performance": {
            "file": "data_loader.py",
            "lines": "497-596",
            "issue": "Fails to find daily_player_json_name",
            "affects": "recent_avg, all daily-based stats"
        },
        "aggregate_2025_player_stats_from_daily": {
            "file": "data_loader.py", 
            "lines": "102-194",
            "issue": "Can't aggregate player stats from daily files",
            "affects": "ab_due, hits_due, streak analysis"
        },
        "match_player_name_to_roster": {
            "file": "utils.py",
            "lines": "120-165", 
            "issue": "Fuzzy matching logic inconsistencies",
            "affects": "All roster → daily file lookups"
        },
        "clean_player_name": {
            "file": "utils.py",
            "lines": "9-36",
            "issue": "May be changing 'A. Garcia' to 'A Garcia'",
            "affects": "Name standardization for matching"
        }
    }
    
    print("📊 FUNCTIONS REQUIRING FIXES:")
    for func_name, details in functions_to_fix.items():
        print(f"\n• {func_name}():")
        print(f"  File: {details['file']} (lines {details['lines']})")
        print(f"  Issue: {details['issue']}")
        print(f"  Affects: {details['affects']}")
    
    print("\n🎯 BATCH vs SINGLE ANALYSIS IMPACT:")
    print("• SINGLE: Uses same pitcher for all players → same lookup failure")
    print("• BATCH: Different pitcher per player → more lookup opportunities to fail")
    print("• PITCHER STATS: P Home HR Total, P HR/Game → depend on pitcher lookups")
    print("• PLAYER STATS: recent_avg, ab_due, hits_due → depend on player lookups")
    
    return generate_fix_strategy()

def generate_fix_strategy():
    """Generate comprehensive fix strategy"""
    print("\n🚀 COMPREHENSIVE FIX STRATEGY:")
    print("="*40)
    
    fix_priorities = [
        {
            "priority": "CRITICAL",
            "task": "Fix name lookup chain in get_last_n_games_performance()",
            "approach": "Improve roster → daily name mapping logic",
            "impact": "Fixes recent_avg, all daily-based player stats"
        },
        {
            "priority": "HIGH", 
            "task": "Enhance match_player_name_to_roster() function",
            "approach": "Better fuzzy matching, team validation, case handling",
            "impact": "Improves all roster/daily file connections"
        },
        {
            "priority": "HIGH",
            "task": "Fix pitcher stat lookups",
            "approach": "Ensure pitcher names properly resolved in daily files", 
            "impact": "Fixes P Home HR Total, P HR/Game, P Home K Total"
        },
        {
            "priority": "MEDIUM",
            "task": "Add comprehensive name mapping debug logging",
            "approach": "Log every lookup attempt with success/failure reasons",
            "impact": "Easier debugging of future name issues"
        },
        {
            "priority": "LOW",
            "task": "Create name mapping validation tool",
            "approach": "Script to test all roster → daily file mappings",
            "impact": "Proactive identification of mapping issues"
        }
    ]
    
    print("📋 FIX PRIORITIES:")
    for fix in fix_priorities:
        print(f"\n{fix['priority']}: {fix['task']}")
        print(f"  Approach: {fix['approach']}")
        print(f"  Impact: {fix['impact']}")
    
    print("\n✅ EXPECTED RESULTS AFTER FIXES:")
    print("• recent_avg: Should show actual batting averages, not 0")
    print("• ab_due/hits_due: Should show meaningful due factors")
    print("• P Home HR Total: Should show pitcher-specific HR totals")
    print("• heating_up/cold: Should properly analyze recent trends")
    print("• All daily-based stats: Should populate with real data")
    
    return True

if __name__ == "__main__":
    analyze_name_matching_issue()