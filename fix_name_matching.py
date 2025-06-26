#!/usr/bin/env python3
"""
Comprehensive fix for name matching issues in BaseballAPI
Addresses the core problem causing statistics to return 0 in PinheadsPlayhouse
"""

import json
import os
import re
from typing import Dict, List, Optional, Tuple

def enhanced_clean_player_name(name_input):
    """
    Enhanced name cleaning that preserves more matching opportunities
    """
    if not name_input or str(name_input).strip() == '':
        return None
    
    name = str(name_input).strip()
    
    # Handle "LastName, FirstName" format (from CSV)
    if ',' in name: 
        parts = name.split(',', 1)
        if len(parts) == 2:
            name = f"{parts[1].strip()} {parts[0].strip()}"
    
    # Standardize whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Title case but preserve some patterns
    name = name.title()
    
    # Standardize suffixes (Jr, Sr, I, II, III, IV)
    name = re.sub(r'\s+(Jr|Sr|Ii|Iii|Iv)\.?$', 
                  lambda m: f" {m.group(1).upper().replace('II','II').replace('III','III').replace('IV','IV')}", 
                  name, flags=re.IGNORECASE)
    
    return name

def create_name_variants(name):
    """
    Create multiple name variants for robust matching
    """
    if not name:
        return []
    
    variants = set()
    
    # Original name
    variants.add(name)
    
    # With and without periods
    name_with_periods = re.sub(r'(?<=\b[A-Z])(?=\s)', '.', name)  # Add periods
    name_without_periods = re.sub(r'(?<=\b[A-Z])\.(?=\s|$)', '', name)  # Remove periods
    
    variants.add(name_with_periods)
    variants.add(name_without_periods)
    
    # Case variations
    variants.add(name.upper())
    variants.add(name.lower())
    variants.add(name.title())
    
    # Remove empty variants
    return [v for v in variants if v and v.strip()]

def enhanced_find_daily_player_name(player_full_name_resolved, roster_data_list, daily_data):
    """
    Enhanced function to find daily player name with multiple fallback strategies
    """
    
    print(f"🔍 Finding daily name for: '{player_full_name_resolved}'")
    
    # Strategy 1: Direct roster lookup (fullName → name)
    daily_player_json_name = None
    for p_info_roster in roster_data_list:
        roster_full_cleaned = p_info_roster.get('fullName_cleaned', '')
        if roster_full_cleaned == player_full_name_resolved:
            daily_player_json_name = p_info_roster.get('name')
            print(f"✅ Strategy 1 success: {player_full_name_resolved} → {daily_player_json_name}")
            break
    
    # Strategy 2: Enhanced roster lookup with variants
    if not daily_player_json_name:
        for p_info_roster in roster_data_list:
            # Try both fullName and fullName_cleaned
            full_names_to_check = [
                p_info_roster.get('fullName', ''),
                p_info_roster.get('fullName_cleaned', ''),
                p_info_roster.get('fullName_resolved', '')
            ]
            
            for full_name_check in full_names_to_check:
                if full_name_check and full_name_check == player_full_name_resolved:
                    daily_player_json_name = p_info_roster.get('name')
                    print(f"✅ Strategy 2 success: {player_full_name_resolved} → {daily_player_json_name}")
                    break
            
            if daily_player_json_name:
                break
    
    # Strategy 3: Fuzzy matching with name variants
    if not daily_player_json_name:
        player_variants = create_name_variants(player_full_name_resolved)
        
        for p_info_roster in roster_data_list:
            roster_variants = create_name_variants(p_info_roster.get('fullName_cleaned', ''))
            
            # Check if any variants match
            for player_variant in player_variants:
                for roster_variant in roster_variants:
                    if player_variant.lower() == roster_variant.lower():
                        daily_player_json_name = p_info_roster.get('name')
                        print(f"✅ Strategy 3 success: '{player_variant}' matched '{roster_variant}' → {daily_player_json_name}")
                        break
                if daily_player_json_name:
                    break
            if daily_player_json_name:
                break
    
    # Strategy 4: Search in daily data directly
    if not daily_player_json_name and daily_data:
        print(f"⚠️  Trying Strategy 4: Direct daily data search")
        
        # Check recent games for name patterns
        temp_dates = sorted(daily_data.keys(), reverse=True)[:5]
        for date_str_rev in temp_dates:
            day_data_rev = daily_data[date_str_rev]
            
            for player_daily_stat_rev in day_data_rev.get('players', []):
                daily_name = player_daily_stat_rev.get('name', '')
                
                # Try matching daily name to our target
                daily_variants = create_name_variants(daily_name)
                player_variants = create_name_variants(player_full_name_resolved)
                
                for daily_variant in daily_variants:
                    for player_variant in player_variants:
                        if daily_variant.lower() == player_variant.lower():
                            daily_player_json_name = daily_name
                            print(f"✅ Strategy 4 success: Found '{daily_name}' in daily data")
                            break
                    if daily_player_json_name:
                        break
                if daily_player_json_name:
                    break
            if daily_player_json_name:
                break
    
    if not daily_player_json_name:
        print(f"❌ All strategies failed for: '{player_full_name_resolved}'")
        
        # Debug info
        print("📊 Available roster entries:")
        for i, p in enumerate(roster_data_list[:5]):  # Show first 5
            print(f"  {i+1}. name: '{p.get('name', '')}', fullName: '{p.get('fullName', '')}', fullName_cleaned: '{p.get('fullName_cleaned', '')}'")
        
        if daily_data:
            recent_date = max(daily_data.keys())
            players_in_recent = daily_data[recent_date].get('players', [])[:5]
            print(f"📊 Players in recent daily data ({recent_date}):")
            for i, p in enumerate(players_in_recent):
                print(f"  {i+1}. name: '{p.get('name', '')}', team: '{p.get('team', '')}'")
    
    return daily_player_json_name

def enhanced_match_player_name_to_roster(short_name_cleaned, roster_data_list, team_filter=None):
    """
    Enhanced player name matching with team validation and better fuzzy logic
    """
    if not short_name_cleaned:
        return None
    
    print(f"🔍 Matching short name: '{short_name_cleaned}'" + (f" (team: {team_filter})" if team_filter else ""))
    
    # Create variants for the short name
    short_name_variants = create_name_variants(short_name_cleaned)
    
    # Strategy 1: Direct match with team validation
    for player in roster_data_list:
        player_name_cleaned = player.get('name_cleaned', '')
        player_team = player.get('team', '')
        
        if player_name_cleaned in short_name_variants:
            if not team_filter or player_team == team_filter:
                result = player.get('fullName_cleaned')
                print(f"✅ Direct match: '{short_name_cleaned}' → '{result}'" + (f" (team: {player_team})" if team_filter else ""))
                return result
    
    # Strategy 2: Abbreviated name expansion with team validation
    if '.' in short_name_cleaned or (len(short_name_cleaned.split()) == 2 and len(short_name_cleaned.split()[0]) <= 2):
        parts = short_name_cleaned.replace('.', '').split()
        if len(parts) >= 2:
            first_initial_part = parts[0].upper()
            last_name_query_part = " ".join(parts[1:]).title()
            
            potential_matches = []
            for player in roster_data_list:
                full_name_roster_cleaned = player.get('fullName_cleaned', '')
                player_team = player.get('team', '')
                
                if full_name_roster_cleaned:
                    full_parts_roster = full_name_roster_cleaned.split()
                    if len(full_parts_roster) >= 2:
                        roster_first_name = full_parts_roster[0]
                        roster_last_name = " ".join(full_parts_roster[1:]).title()
                        
                        if (roster_first_name.upper().startswith(first_initial_part) and 
                            roster_last_name == last_name_query_part):
                            
                            if not team_filter or player_team == team_filter:
                                potential_matches.append({
                                    'full_name': full_name_roster_cleaned,
                                    'team': player_team
                                })
            
            if len(potential_matches) == 1:
                result = potential_matches[0]['full_name']
                print(f"✅ Abbreviated expansion: '{short_name_cleaned}' → '{result}'" + (f" (team: {potential_matches[0]['team']})" if team_filter else ""))
                return result
            elif len(potential_matches) > 1:
                print(f"⚠️  Multiple matches for '{short_name_cleaned}': {[m['full_name'] for m in potential_matches]}")
                if team_filter:
                    # If we have team filter, pick the matching team
                    team_matches = [m for m in potential_matches if m['team'] == team_filter]
                    if len(team_matches) == 1:
                        result = team_matches[0]['full_name']
                        print(f"✅ Team-filtered match: '{short_name_cleaned}' → '{result}' (team: {team_filter})")
                        return result
    
    # Strategy 3: Fuzzy matching with team preference
    from difflib import get_close_matches
    
    # Try fuzzy match on short names first
    roster_short_names = []
    roster_short_to_full = {}
    for p in roster_data_list:
        short_name = p.get('name_cleaned', '')
        full_name = p.get('fullName_cleaned', '')
        team = p.get('team', '')
        
        if short_name and full_name:
            roster_short_names.append(short_name)
            roster_short_to_full[short_name] = {'full_name': full_name, 'team': team}
    
    matches = get_close_matches(short_name_cleaned, roster_short_names, n=3, cutoff=0.8)
    if matches:
        best_match = matches[0]
        match_info = roster_short_to_full[best_match]
        
        if not team_filter or match_info['team'] == team_filter:
            result = match_info['full_name']
            print(f"✅ Fuzzy short name match: '{short_name_cleaned}' → '{result}'" + (f" (team: {match_info['team']})" if team_filter else ""))
            return result
    
    # Strategy 4: Fuzzy match on full names
    roster_full_names = []
    roster_full_to_team = {}
    for p in roster_data_list:
        full_name = p.get('fullName_cleaned', '')
        team = p.get('team', '')
        
        if full_name:
            roster_full_names.append(full_name)
            roster_full_to_team[full_name] = team
    
    full_matches = get_close_matches(short_name_cleaned, roster_full_names, n=3, cutoff=0.75)
    if full_matches:
        best_match = full_matches[0]
        match_team = roster_full_to_team[best_match]
        
        if not team_filter or match_team == team_filter:
            print(f"✅ Fuzzy full name match: '{short_name_cleaned}' → '{best_match}'" + (f" (team: {match_team})" if team_filter else ""))
            return best_match
    
    print(f"❌ No match found for: '{short_name_cleaned}'" + (f" (team: {team_filter})" if team_filter else ""))
    return None

def test_name_matching_fixes():
    """
    Test the enhanced name matching functions
    """
    print("🧪 TESTING ENHANCED NAME MATCHING")
    print("="*50)
    
    # Test name variants
    test_names = ["A. Garcia", "Aramis Garcia", "J. Rodriguez", "Jose Rodriguez"]
    
    for name in test_names:
        variants = create_name_variants(name)
        print(f"\nVariants for '{name}':")
        for variant in variants:
            print(f"  - '{variant}'")
    
    # Test enhanced cleaning
    test_cases = [
        "A. Garcia",
        "Garcia, Aramis", 
        "J.  Rodriguez",
        "Martinez Jr."
    ]
    
    print(f"\n🧹 TESTING ENHANCED CLEANING:")
    for case in test_cases:
        cleaned = enhanced_clean_player_name(case)
        print(f"'{case}' → '{cleaned}'")
    
    return True

if __name__ == "__main__":
    test_name_matching_fixes()