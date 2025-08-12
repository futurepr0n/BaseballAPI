import pandas as pd
import numpy as np
import re
import os
import json
from difflib import get_close_matches
from collections import defaultdict
import unicodedata

def clean_player_name(name_input):
    """
    Bulletproof player name normalization for special characters.
    Converts ANY international character to English equivalent.
    Ensures rosters.json compatibility.
    """
    if pd.isna(name_input):
        return None
    
    name = str(name_input)
    
    # Comprehensive character mapping for all international characters
    accent_map = {
        # Spanish/Latin characters
        'á': 'a', 'à': 'a', 'ä': 'a', 'â': 'a', 'ā': 'a', 'ą': 'a', 'å': 'a', 'ã': 'a',
        'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e', 'ē': 'e', 'ę': 'e',
        'í': 'i', 'ì': 'i', 'ï': 'i', 'î': 'i', 'ī': 'i', 'į': 'i',
        'ó': 'o', 'ò': 'o', 'ö': 'o', 'ô': 'o', 'ō': 'o', 'ø': 'o', 'õ': 'o',
        'ú': 'u', 'ù': 'u', 'ü': 'u', 'û': 'u', 'ū': 'u', 'ų': 'u',
        'ñ': 'n', 'ń': 'n', 'ç': 'c', 'č': 'c', 'ć': 'c',
        'ř': 'r', 'ś': 's', 'š': 's', 'ť': 't', 'ý': 'y', 'ž': 'z', 'ź': 'z',
        # Capital letters
        'Á': 'A', 'À': 'A', 'Ä': 'A', 'Â': 'A', 'Ā': 'A', 'Ą': 'A', 'Å': 'A', 'Ã': 'A',
        'É': 'E', 'È': 'E', 'Ë': 'E', 'Ê': 'E', 'Ē': 'E', 'Ę': 'E',
        'Í': 'I', 'Ì': 'I', 'Ï': 'I', 'Î': 'I', 'Ī': 'I', 'Į': 'I',
        'Ó': 'O', 'Ò': 'O', 'Ö': 'O', 'Ô': 'O', 'Ō': 'O', 'Ø': 'O', 'Õ': 'O',
        'Ú': 'U', 'Ù': 'U', 'Ü': 'U', 'Û': 'U', 'Ū': 'U', 'Ų': 'U',
        'Ñ': 'N', 'Ń': 'N', 'Ç': 'C', 'Č': 'C', 'Ć': 'C',
        'Ř': 'R', 'Ś': 'S', 'Š': 'S', 'Ť': 'T', 'Ý': 'Y', 'Ž': 'Z', 'Ź': 'Z'
    }
    
    # Replace each character using our mapping
    normalized = ''
    for char in name:
        normalized += accent_map.get(char, char)
    
    # Handle "LastName, FirstName" format
    if ',' in normalized: 
        parts = normalized.split(',', 1)
        if len(parts) == 2:
            normalized = f"{parts[1].strip()} {parts[0].strip()}"
    
    # Standardize whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip().title()
    
    # Standardize suffixes (Jr, Sr, I, II, III, IV)
    normalized = re.sub(r'\s+(Jr|Sr|Ii|Iii|Iv)\.?$', 
                       lambda m: f" {m.group(1).upper().replace('II','II').replace('III','III').replace('IV','IV')}", 
                       normalized, flags=re.IGNORECASE)
    
    # Remove periods from initials
    normalized = re.sub(r'(?<=\b[A-Z])\.(?=\s|$)', '', normalized)
    
    return normalized

def robust_json_load(file_path):
    """Safely load a JSON file with error handling."""
    if not os.path.exists(file_path):
        print(f"Warning: JSON file not found - {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR loading {file_path}: {e}")
        return []

def robust_csv_load(filename, year=None,
                    id_column_options=['player_id', 'id'],
                    name_column_options=['last_name, first_name', 'name', 'fullName'],
                    pitch_type_column_options=['pitch_type', 'api_pitch_type_group03']):
    """
    Safely load a CSV file with standardized column handling.
    Supports loading different year versions of the same file.
    Uses centralized data path from config.
    """
    from config import DATA_PATH  # Import centralized path
    
    if year:
        base_name = filename.replace('2025', str(year))
        file_path = os.path.join(DATA_PATH, base_name)
    else:
        file_path = os.path.join(DATA_PATH, filename)
    
    if not os.path.exists(file_path):
        print(f"Warning: CSV File not found - {file_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(file_path, low_memory=False)
        
        # Add year column
        if year:
            df['year'] = year
        
        # Process ID column
        id_col = next((opt for opt in id_column_options if opt in df.columns), None)
        if id_col:
            df.rename(columns={id_col: 'mlbam_id'}, inplace=True)
            df['mlbam_id'] = pd.to_numeric(df['mlbam_id'], errors='coerce').dropna().astype(int).astype(str)
        
        # Process name column
        parsed_name_col = None
        for name_opt in name_column_options:
            if name_opt in df.columns:
                df['parsed_fullName'] = df[name_opt].apply(clean_player_name)
                parsed_name_col = 'parsed_fullName'
                break
                
        if not parsed_name_col and 'first_name' in df.columns and 'last_name' in df.columns:
            df['parsed_fullName'] = (df['first_name'].astype(str) + " " + df['last_name'].astype(str)).apply(clean_player_name)
        
        # Process pitch type column
        pt_col = next((opt for opt in pitch_type_column_options if opt in df.columns and opt != 'pitch_type'), None)
        if pt_col:
            df.rename(columns={pt_col: 'pitch_type'}, inplace=True)
        
        # Convert numeric columns
        skip_numeric = ['mlbam_id', 'pitch_type', 'parsed_fullName', 'year', 'team_name_alt', 'pitch_name'] + \
                      name_column_options + id_column_options + pitch_type_column_options + \
                      ['name', 'last_name, first_name', 'fullName', 'first_name', 'last_name']
                      
        for col in df.columns:
            if col not in skip_numeric:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except Exception as e:
        print(f"ERROR processing {file_path}: {e}")
        return pd.DataFrame()

def get_approximated_pa(stats_dict):
    """Calculate approximate plate appearances from available stats."""
    if not isinstance(stats_dict, dict):
        return 0
    
    return stats_dict.get('AB', 0) + stats_dict.get('BB', 0) + stats_dict.get('HBP', 0) + \
           stats_dict.get('SF', 0) + stats_dict.get('SAC', 0)

def match_player_name_to_roster(short_name_cleaned, roster_data_list):
    """
    Enhanced player name matching to fix 0 statistics issue.
    Matches a short/abbreviated player name to full roster name with multiple strategies.
    Now handles special characters by normalizing them.
    """
    if not short_name_cleaned:
        return None
    
    # Normalize the input name to handle special characters
    short_name_normalized = unicodedata.normalize('NFD', short_name_cleaned)
    short_name_normalized = ''.join(char for char in short_name_normalized if unicodedata.category(char) != 'Mn')
    
    # Strategy 1: Direct exact match (case sensitive) - try both original and normalized
    for player in roster_data_list:
        if player.get('name_cleaned') == short_name_cleaned:
            return player.get('fullName_cleaned')
        # Also try normalized comparison
        if player.get('name_cleaned') == short_name_normalized:
            return player.get('fullName_cleaned')
    
    # Strategy 2: Case-insensitive direct match
    short_name_lower = short_name_cleaned.lower()
    short_name_normalized_lower = short_name_normalized.lower()
    for player in roster_data_list:
        name_cleaned = player.get('name_cleaned', '')
        name_cleaned_lower = name_cleaned.lower()
        if name_cleaned_lower == short_name_lower or name_cleaned_lower == short_name_normalized_lower:
            return player.get('fullName_cleaned')
    
    # Strategy 3: Match against original name field (before cleaning)
    for player in roster_data_list:
        original_name = player.get('name', '')
        if original_name == short_name_cleaned:
            return player.get('fullName_cleaned')
        # Also try case-insensitive match on original name
        if original_name.lower() == short_name_lower:
            return player.get('fullName_cleaned')
    
    # Strategy 4: Enhanced abbreviated name handling with period flexibility
    # Handle names like "A. Garcia", "A Garcia", "A.Garcia"
    if ('.' in short_name_cleaned or 
        (len(short_name_cleaned.split()) == 2 and len(short_name_cleaned.split()[0]) <= 2)):
        
        # Create multiple variants of the short name
        variants = []
        
        # Original
        variants.append(short_name_cleaned)
        
        # With/without periods
        with_period = short_name_cleaned.replace(' ', '. ', 1) if '.' not in short_name_cleaned else short_name_cleaned
        without_period = short_name_cleaned.replace('.', '')
        variants.extend([with_period, without_period])
        
        # Different spacing
        variants.append(short_name_cleaned.replace(' ', ''))
        variants.append(short_name_cleaned.replace('.', '. '))
        
        for variant in variants:
            parts = variant.replace('.', '').split()
            if len(parts) >= 2:
                first_initial_part = parts[0].upper()
                last_name_query_part = " ".join(parts[1:]).title()
                
                potential_matches = []
                for player in roster_data_list:
                    full_name_roster_cleaned = player.get('fullName_cleaned', '')
                    if full_name_roster_cleaned:
                        full_parts_roster = full_name_roster_cleaned.split()
                        if len(full_parts_roster) >= 2:
                            roster_first_name = full_parts_roster[0]
                            roster_last_name = " ".join(full_parts_roster[1:]).title()
                            
                            # Enhanced matching: check if first name starts with initial
                            if (roster_first_name.upper().startswith(first_initial_part) and 
                                roster_last_name.lower() == last_name_query_part.lower()):
                                potential_matches.append(full_name_roster_cleaned)
                
                if len(potential_matches) == 1:
                    return potential_matches[0]
                elif len(potential_matches) > 1:
                    # Multiple matches - return first one (could be enhanced with team matching)
                    return potential_matches[0]
    
    # Strategy 5: Fuzzy match on multiple name fields
    from difflib import get_close_matches
    
    # Try fuzzy matching on name_cleaned
    roster_short_names = [p.get('name_cleaned', '') for p in roster_data_list if p.get('name_cleaned')]
    matches = get_close_matches(short_name_cleaned, roster_short_names, n=1, cutoff=0.8)
    if matches:
        for player in roster_data_list:
            if player.get('name_cleaned') == matches[0]:
                return player.get('fullName_cleaned')
    
    # Try fuzzy matching on original name field
    roster_original_names = [p.get('name', '') for p in roster_data_list if p.get('name')]
    original_matches = get_close_matches(short_name_cleaned, roster_original_names, n=1, cutoff=0.8)
    if original_matches:
        for player in roster_data_list:
            if player.get('name') == original_matches[0]:
                return player.get('fullName_cleaned')
    
    # Strategy 6: Fuzzy match on full names (lower cutoff for more flexibility)
    roster_full_names = [p.get('fullName_cleaned', '') for p in roster_data_list if p.get('fullName_cleaned')]
    full_matches = get_close_matches(short_name_cleaned, roster_full_names, n=1, cutoff=0.7)
    if full_matches:
        return full_matches[0]
    
    # Strategy 7: Last resort - partial matching
    for player in roster_data_list:
        full_name = player.get('fullName_cleaned', '')
        if full_name and short_name_cleaned.lower() in full_name.lower():
            # Basic sanity check - make sure it's not too broad a match
            if len(short_name_cleaned) >= 4:  # Don't match very short strings
                return full_name
    
    return None

def normalize_calculated(value, metric_name, metric_ranges, scale=100, higher_is_better=True):
    """
    Normalize a stat value within a pre-calculated range.
    Returns a value from 0-scale where higher values are better (or worse if higher_is_better=False).
    """
    if pd.isna(value) or not isinstance(value, (int, float)):
        return 0
    
    range_info = metric_ranges.get(metric_name)
    if not range_info:
        if (isinstance(value, float) and 0.0 <= value <= 1.0 and 
            any(substr in metric_name.lower() for substr in ['rate', 'percent', 'avg', 'slg', 'obp', 'woba', 'iso'])):
            norm_val = value
            if not higher_is_better:
                norm_val = 1.0 - norm_val
            return max(0, min(1, norm_val)) * scale
        return scale/2  # Neutral if no range and not a typical rate
    
    min_v, max_v = range_info['min'], range_info['max']
    if max_v == min_v:
        return scale/2 if value >= min_v else 0
    
    norm = (value - min_v) / (max_v - min_v)
    if not higher_is_better:
        norm = 1 - norm
    
    return max(0, min(1, norm)) * scale

def calculate_metric_ranges(master_player_data):
    """Calculate min/max ranges for various metrics for normalization."""
    print("\nCalculating metric ranges for normalization...")
    all_metrics_values = defaultdict(list)
    
    for pid, pdata in master_player_data.items():
        # Batter exit velocity stats
        ev_stats = pdata.get('hitter_overall_ev_stats', {})
        if isinstance(ev_stats, dict):
            if pd.notna(ev_stats.get('brl_percent')):
                all_metrics_values['brl_percent'].append(ev_stats.get('brl_percent') / 100.0)
            if pd.notna(ev_stats.get('hard_hit_percent')):
                all_metrics_values['hard_hit_percent'].append(ev_stats.get('hard_hit_percent') / 100.0)
            if pd.notna(ev_stats.get('slg_percent')):
                all_metrics_values['slg'].append(ev_stats.get('slg_percent'))
            
            iso_val = ev_stats.get('iso_percent')
            if pd.notna(iso_val):
                all_metrics_values['iso'].append(iso_val)
            elif pd.notna(ev_stats.get('slg_percent')) and pd.notna(ev_stats.get('batting_avg')):
                all_metrics_values['iso'].append(ev_stats.get('slg_percent') - ev_stats.get('batting_avg'))
        
        # Pitcher exit velocity stats
        pev_stats = pdata.get('pitcher_overall_ev_stats', {})
        if isinstance(pev_stats, dict):
            if pd.notna(pev_stats.get('brl_percent')):
                all_metrics_values['brl_percent'].append(pev_stats.get('brl_percent') / 100.0)
            if pd.notna(pev_stats.get('hard_hit_percent')):
                all_metrics_values['hard_hit_percent'].append(pev_stats.get('hard_hit_percent') / 100.0)
            if pd.notna(pev_stats.get('slg_percent')):
                all_metrics_values['slg'].append(pev_stats.get('slg_percent'))
        
        # Hitter pitch arsenal stats
        h_arsenal = pdata.get('hitter_pitch_arsenal_stats', {})
        if isinstance(h_arsenal, dict):
            for pitch_type, stats_dict in h_arsenal.items():
                if isinstance(stats_dict, dict):
                    if pd.notna(stats_dict.get('slg')):
                        all_metrics_values['slg'].append(stats_dict.get('slg'))
                    if pd.notna(stats_dict.get('woba')):
                        all_metrics_values['woba'].append(stats_dict.get('woba'))
                    if pd.notna(stats_dict.get('hr')):
                        all_metrics_values['hr'].append(stats_dict.get('hr'))
                    if pd.notna(stats_dict.get('hard_hit_percent')):
                        all_metrics_values['hard_hit_percent'].append(stats_dict.get('hard_hit_percent') / 100.0)
                    if pd.notna(stats_dict.get('run_value_per_100')):
                        all_metrics_values['run_value_per_100'].append(stats_dict.get('run_value_per_100'))
                    if pd.notna(stats_dict.get('k_percent')):
                        all_metrics_values['k_rate'].append(stats_dict.get('k_percent') / 100.0)
        
        # Pitcher pitch arsenal stats
        p_arsenal = pdata.get('pitcher_pitch_arsenal_stats', {})
        if isinstance(p_arsenal, dict):
            for pitch_type, stats_dict in p_arsenal.items():
                if isinstance(stats_dict, dict):
                    if pd.notna(stats_dict.get('slg')):
                        all_metrics_values['slg'].append(stats_dict.get('slg'))
                    if pd.notna(stats_dict.get('woba')):
                        all_metrics_values['woba'].append(stats_dict.get('woba'))
                    if pd.notna(stats_dict.get('hr')):
                        all_metrics_values['hr'].append(stats_dict.get('hr'))
                    if pd.notna(stats_dict.get('hard_hit_percent')):
                        all_metrics_values['hard_hit_percent'].append(stats_dict.get('hard_hit_percent') / 100.0)
                    if pd.notna(stats_dict.get('run_value_per_100')):
                        all_metrics_values['run_value_per_100'].append(stats_dict.get('run_value_per_100'))
                    if pd.notna(stats_dict.get('k_percent')):
                        all_metrics_values['k_rate'].append(stats_dict.get('k_percent') / 100.0)
                    if pd.notna(stats_dict.get('pitch_usage')):
                        all_metrics_values['pitch_usage'].append(stats_dict.get('pitch_usage'))
        
        # Batted ball stats
        bbb_data = pdata.get('batted_ball_stats', {})
        if isinstance(bbb_data, dict):
            for matchup_key, pitch_dict_val in bbb_data.items():
                if isinstance(pitch_dict_val, dict):
                    for pitch_type, stats_dict in pitch_dict_val.items():
                        if isinstance(stats_dict, dict):
                            if pd.notna(stats_dict.get('fb_rate')):
                                all_metrics_values['fb_rate'].append(stats_dict.get('fb_rate'))
                            if pd.notna(stats_dict.get('pull_air_rate')):
                                all_metrics_values['pull_air_rate'].append(stats_dict.get('pull_air_rate'))
    
    # Default ranges if calculation fails
    default_metric_ranges_fallback = {
        'fb_rate': {'min': 0.1, 'max': 0.6},
        'pull_air_rate': {'min': 0.1, 'max': 0.6},
        'slg': {'min': 0.1, 'max': 1.0},
        'woba': {'min': 0.1, 'max': 0.6},
        'hr': {'min': 0, 'max': 25},
        'iso': {'min': 0.0, 'max': 0.5},
        'brl_percent': {'min': 0.0, 'max': 0.3},
        'hard_hit_percent': {'min': 0.15, 'max': 0.7},
        'run_value_per_100': {'min': -10, 'max': 10},
        'pitch_usage': {'min': 0, 'max': 100},
        'k_rate': {'min': 0.05, 'max': 0.5},
        'hit_rate': {'min': 0.1, 'max': 0.5},
        'hr_rate': {'min': 0.0, 'max': 0.15},
        'obp': {'min': 0.2, 'max': 0.5}
    }
    
    metric_ranges_calculated = {}
    for metric, values_list in all_metrics_values.items():
        valid_values = [v for v in values_list if pd.notna(v) and isinstance(v, (int, float))]
        if valid_values:
            series = pd.Series(valid_values)
            min_val, max_val = series.quantile(0.02), series.quantile(0.98)
            
            if min_val == max_val:
                min_val, max_val = series.min(), series.max()
            
            if min_val == max_val:
                min_val, max_val = default_metric_ranges_fallback.get(metric, {'min': 0})['min'], \
                                   default_metric_ranges_fallback.get(metric, {'max': 1})['max']
            
            metric_ranges_calculated[metric] = {'min': min_val, 'max': max_val}
        else:
            metric_ranges_calculated[metric] = default_metric_ranges_fallback.get(metric, {'min': 0, 'max': 1})
    
    print("Metric ranges calculation complete.")
    return metric_ranges_calculated

def adjust_stat_with_confidence(player_stat_value, player_pa, stat_name_key_in_league_avg, 
                                league_avg_stats, k_confidence_pa=100, default_league_avg_override=None):
    """
    Adjust a player stat based on sample size confidence.
    For small samples, regress toward league average.
    """
    league_avg_for_stat = league_avg_stats.get(stat_name_key_in_league_avg, default_league_avg_override)
    
    if (pd.isna(player_stat_value) or league_avg_for_stat is None or 
        player_pa is None or pd.isna(player_pa) or player_pa < 0):
        return player_stat_value
    
    confidence = player_pa / (player_pa + k_confidence_pa)
    return confidence * player_stat_value + (1 - confidence) * league_avg_for_stat

def find_player_id_by_name(name_query, player_type_filter, master_player_data, name_to_id_map):
    """Find a player's ID based on their name, with optional filtering by player type."""
    cleaned_query_name = clean_player_name(name_query)
    if not cleaned_query_name:
        return None
    
    # Direct lookup in name map
    player_id = name_to_id_map.get(cleaned_query_name)
    if player_id and (not player_type_filter or 
                     master_player_data.get(player_id, {}).get('roster_info', {}).get('type') == player_type_filter):
        return player_id
    
    # Search through master data
    for pid, pdata in master_player_data.items():
        if player_type_filter and pdata.get('roster_info', {}).get('type') != player_type_filter:
            continue
            
        r_info = pdata.get('roster_info', {})
        names_to_check = [
            r_info.get('fullName_resolved'), 
            r_info.get('fullName_cleaned'), 
            r_info.get('name_cleaned')
        ]
        
        if 'parsed_fullName' in r_info and r_info['parsed_fullName'] not in names_to_check:
            names_to_check.append(r_info['parsed_fullName'])
        
        for name_variant in names_to_check:
            if name_variant and clean_player_name(name_variant) == cleaned_query_name:
                return pid
    
    # Fuzzy matching as last resort
    all_roster_full_names_resolved = [p.get('roster_info', {}).get('fullName_resolved') 
                                      for p in master_player_data.values() 
                                      if p.get('roster_info', {}).get('fullName_resolved')]
    
    candidate_names_for_fuzzy = []
    if player_type_filter:
        for pid_f, pdata_f in master_player_data.items():
            if pdata_f.get('roster_info', {}).get('type') == player_type_filter:
                name_res = pdata_f.get('roster_info', {}).get('fullName_resolved')
                if name_res:
                    candidate_names_for_fuzzy.append(name_res)
        
        fuzzy_matches = get_close_matches(cleaned_query_name, candidate_names_for_fuzzy, n=1, cutoff=0.8)
    else:
        fuzzy_matches = get_close_matches(cleaned_query_name, all_roster_full_names_resolved, n=1, cutoff=0.8)
    
    if fuzzy_matches:
        matched_name_resolved = fuzzy_matches[0]
        for pid_fuzzy, pdata_fuzzy in master_player_data.items():
            if player_type_filter and pdata_fuzzy.get('roster_info', {}).get('type') != player_type_filter:
                continue
                
            if pdata_fuzzy.get('roster_info', {}).get('fullName_resolved') == matched_name_resolved:
                return pid_fuzzy
    
    return None
