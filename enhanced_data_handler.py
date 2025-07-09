"""
Enhanced data handling for BaseballAPI with missing pitcher data fallbacks.
Provides robust analysis even when Baseball Savant scraping fails.
"""

import numpy as np
import pandas as pd
from collections import defaultdict
import logging
from typing import Dict, List, Optional, Tuple, Any

from enhanced_analyzer import (
    calculate_league_averages_by_pitch_type,
    enhanced_arsenal_matchup_with_fallbacks,
    enhanced_hr_score_with_missing_data_handling,
    LEAGUE_AVERAGE_PITCH_DISTRIBUTION,
    LEAGUE_AVERAGE_PERFORMANCE_BY_PITCH
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDataHandler:
    """
    Handles missing pitcher data scenarios with multiple fallback strategies.
    """
    
    def __init__(self, master_player_data: Dict, league_avg_stats: Dict, metric_ranges: Dict, 
                 roster_data: List = None, daily_game_data: Dict = None):
        self.master_player_data = master_player_data
        self.league_avg_stats = league_avg_stats
        self.metric_ranges = metric_ranges
        self.roster_data = roster_data or []
        self.daily_game_data = daily_game_data or {}
        
        # Calculate real-time league averages by pitch type
        self.league_avg_by_pitch_type = calculate_league_averages_by_pitch_type(master_player_data)
        
        # Statistics tracking
        self.analysis_stats = {
            'total_analyses': 0,
            'full_data_analyses': 0,
            'partial_data_analyses': 0,
            'team_based_analyses': 0,
            'league_average_analyses': 0,
            'failed_analyses': 0
        }
        
        logger.info(f"Enhanced data handler initialized with {len(master_player_data)} players")
    
    def analyze_team_matchup_with_fallbacks(self, pitcher_name: str, team_abbr: str, 
                                          sort_by: str = 'score', min_score: float = 0,
                                          include_confidence_metrics: bool = True) -> Dict[str, Any]:
        """
        Analyze pitcher vs team matchup with robust missing data handling.
        
        Args:
            pitcher_name: Name of the pitcher
            team_abbr: Team abbreviation (e.g., 'SEA', 'NYY')
            sort_by: Field to sort results by
            min_score: Minimum score threshold
            include_confidence_metrics: Whether to include data quality metrics
            
        Returns:
            Dictionary containing analysis results with confidence indicators
        """
        # Find pitcher
        pitcher_data = self._find_pitcher_by_name(pitcher_name)
        if not pitcher_data:
            return {
                'error': f"Pitcher '{pitcher_name}' not found",
                'success': False,
                'confidence': 0.0,
                'data_source': 'none'
            }
        
        pitcher_id = pitcher_data['pitcher_id']
        logger.info(f"✅ PITCHER FOUND: {pitcher_data.get('name', 'Unknown')} (ID: {pitcher_id}, Team: {pitcher_data.get('team', 'Unknown')})")
        
        # CRITICAL FIX: Calculate pitcher trend direction ONCE and share across all hitters
        pitcher_trend_data = self._get_pitcher_trend_analysis(pitcher_id, pitcher_data.get('name', 'Unknown'))
        logger.info(f"📈 PITCHER TREND: {pitcher_data.get('name', 'Unknown')} - Direction: {pitcher_trend_data.get('trend_direction', 'unknown')}")
        
        # CALCULATE PITCHER HOME GAME STATS ONCE and share across all hitters
        pitcher_home_stats = self._calculate_comprehensive_pitcher_stats(pitcher_id, pitcher_data.get('name', 'Unknown'))
        logger.info(f"🏠 PITCHER HOME STATS: {pitcher_data.get('name', 'Unknown')} - {pitcher_home_stats.get('pitcher_home_games', 0)} home games")
        
        # Find team batters
        team_batters = self._find_team_batters(team_abbr)
        if not team_batters:
            return {
                'error': f"No batters found for team '{team_abbr}'",
                'success': False,
                'confidence': 0.0,
                'data_source': 'none'
            }
        
        # Analyze each batter vs pitcher
        batter_analyses = []
        total_confidence = 0
        data_source_counts = defaultdict(int)
        
        for batter in team_batters:
            try:
                # Get recent performance for this batter
                recent_stats = self._get_recent_batter_performance(batter['batter_id'])
                
                # NEW: Calculate comprehensive hitter stats from ALL daily data
                hitter_comprehensive_stats = self._calculate_comprehensive_hitter_stats(batter['batter_id'], batter['name'])
                
                # Perform enhanced analysis with shared pitcher data and individual hitter stats
                analysis = enhanced_hr_score_with_missing_data_handling(
                    batter['batter_id'],
                    pitcher_id,
                    self.master_player_data,
                    {},  # historical_data - could be populated if available
                    self.metric_ranges,
                    self.league_avg_stats,
                    self.league_avg_by_pitch_type,
                    recent_stats,
                    pitcher_trend_data,  # CRITICAL FIX: Pass shared pitcher trend data
                    pitcher_home_stats,  # Pass pitcher home game stats
                    hitter_comprehensive_stats  # NEW: Pass comprehensive hitter stats
                )
                
                if analysis.get('score', 0) >= min_score:
                    analysis['player_id'] = batter['batter_id']
                    analysis['team'] = team_abbr.upper()
                    batter_analyses.append(analysis)
                    
                    # Track statistics
                    total_confidence += analysis.get('confidence', 0)
                    data_source_counts[analysis.get('data_source', 'unknown')] += 1
                    self.analysis_stats['total_analyses'] += 1
                    
                    # Categorize analysis type
                    confidence = analysis.get('confidence', 0)
                    if confidence >= 0.8:
                        self.analysis_stats['full_data_analyses'] += 1
                    elif confidence >= 0.5:
                        self.analysis_stats['partial_data_analyses'] += 1
                    elif confidence >= 0.3:
                        self.analysis_stats['team_based_analyses'] += 1
                    else:
                        self.analysis_stats['league_average_analyses'] += 1
                
            except Exception as e:
                logger.error(f"Error analyzing batter {batter.get('name', 'unknown')}: {e}")
                self.analysis_stats['failed_analyses'] += 1
                continue
        
        # Sort results
        if batter_analyses:
            reverse_sort = sort_by not in ['strikeout']  # Strikeout probability - lower is better
            
            if sort_by == 'score':
                batter_analyses.sort(key=lambda x: x.get('score', 0), reverse=reverse_sort)
            elif sort_by in ['hr', 'homerun']:
                batter_analyses.sort(key=lambda x: x.get('outcome_probabilities', {}).get('homerun', 0), reverse=reverse_sort)
            elif sort_by == 'hit':
                batter_analyses.sort(key=lambda x: x.get('outcome_probabilities', {}).get('hit', 0), reverse=reverse_sort)
            elif sort_by == 'reach_base':
                batter_analyses.sort(key=lambda x: x.get('outcome_probabilities', {}).get('reach_base', 0), reverse=reverse_sort)
            elif sort_by == 'strikeout':
                batter_analyses.sort(key=lambda x: x.get('outcome_probabilities', {}).get('strikeout', 100), reverse=False)
            elif sort_by == 'confidence':
                batter_analyses.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Calculate overall analysis quality metrics
        avg_confidence = total_confidence / len(batter_analyses) if batter_analyses else 0
        primary_data_source = max(data_source_counts.items(), key=lambda x: x[1])[0] if data_source_counts else 'none'
        
        # Determine overall reliability
        if avg_confidence >= 0.7:
            reliability = 'high'
        elif avg_confidence >= 0.4:
            reliability = 'medium'
        else:
            reliability = 'low'
        
        result = {
            'success': True,
            'pitcher_name': pitcher_name,
            'pitcher_id': pitcher_id,
            'team': team_abbr.upper(),
            'predictions': batter_analyses,
            'total_batters_analyzed': len(batter_analyses),
            'average_confidence': round(avg_confidence, 3),
            'primary_data_source': primary_data_source,
            'reliability': reliability,
            'sort_by': sort_by,
            'min_score_filter': min_score
        }
        
        if include_confidence_metrics:
            result['data_quality_breakdown'] = {
                'data_source_distribution': dict(data_source_counts),
                'analysis_summary': {
                    'full_pitcher_data': data_source_counts.get('pitcher_specific', 0),
                    'partial_pitcher_data': data_source_counts.get('pitcher_partial', 0),
                    'team_based_estimates': data_source_counts.get('team_based', 0),
                    'league_average_fallbacks': data_source_counts.get('league_average', 0)
                },
                'confidence_distribution': self._calculate_confidence_distribution(batter_analyses),
                'missing_data_impact': self._assess_missing_data_impact(avg_confidence, primary_data_source)
            }
        
        return result
    
    def _find_pitcher_by_name(self, pitcher_name: str) -> Optional[Dict[str, Any]]:
        """Find pitcher by name in master player data with comprehensive Unicode normalization."""
        from utils import clean_player_name
        from difflib import get_close_matches
        
        pitcher_clean = clean_player_name(pitcher_name)
        logger.info(f"🔍 PITCHER SEARCH: '{pitcher_name}' → normalized: '{pitcher_clean}'")
        
        # Strategy 1: Enhanced exact matching with Unicode normalization
        for pid, pdata in self.master_player_data.items():
            roster_info = pdata.get('roster_info', {})
            if roster_info.get('type') == 'pitcher':
                names_to_check = [
                    roster_info.get('fullName_resolved', ''),
                    roster_info.get('fullName_cleaned', ''), 
                    roster_info.get('fullName', ''),
                    roster_info.get('name_cleaned', ''),
                    roster_info.get('name', '')
                ]
                
                for name in names_to_check:
                    if name:
                        # Apply same normalization to database names
                        name_clean = clean_player_name(name)
                        if (name.lower() == pitcher_name.lower() or 
                            name.lower() == pitcher_clean.lower() or
                            name_clean.lower() == pitcher_clean.lower() or
                            name_clean.lower() == pitcher_name.lower()):
                            logger.info(f"✅ PITCHER EXACT MATCH: '{pitcher_name}' → '{name}' (normalized: '{name_clean}')")
                            return {
                                'pitcher_id': pid,
                                'name': roster_info.get('fullName_resolved', pitcher_name),
                                'team': roster_info.get('team', 'UNK')
                            }
        
        # Strategy 2: Enhanced fuzzy matching with normalized names
        all_pitcher_names = []
        all_pitcher_names_normalized = []
        pitcher_name_to_data = {}
        
        for pid, pdata in self.master_player_data.items():
            roster_info = pdata.get('roster_info', {})
            if roster_info.get('type') == 'pitcher':
                for field in ['fullName_resolved', 'fullName_cleaned', 'fullName', 'name_cleaned', 'name']:
                    name = roster_info.get(field, '')
                    if name:
                        name_normalized = clean_player_name(name)
                        all_pitcher_names.append(name)
                        all_pitcher_names_normalized.append(name_normalized)
                        # Store both original and normalized as keys
                        pitcher_name_to_data[name] = {
                            'pitcher_id': pid,
                            'name': roster_info.get('fullName_resolved', name),
                            'team': roster_info.get('team', 'UNK')
                        }
                        pitcher_name_to_data[name_normalized] = {
                            'pitcher_id': pid,
                            'name': roster_info.get('fullName_resolved', name),
                            'team': roster_info.get('team', 'UNK')
                        }
        
        # Try fuzzy matching on normalized names first
        close_matches = get_close_matches(pitcher_clean, all_pitcher_names_normalized, n=1, cutoff=0.8)
        if close_matches:
            matched_name = close_matches[0]
            logger.info(f"🔍 FUZZY NORMALIZED MATCH: '{pitcher_name}' → '{matched_name}'")
            return pitcher_name_to_data[matched_name]
        
        # Try fuzzy matching on original names as fallback
        close_matches = get_close_matches(pitcher_name, all_pitcher_names, n=1, cutoff=0.8)
        if close_matches:
            matched_name = close_matches[0]
            logger.info(f"🔍 FUZZY ORIGINAL MATCH: '{pitcher_name}' → '{matched_name}'")
            return pitcher_name_to_data[matched_name]
        
        logger.warning(f"❌ Pitcher not found: '{pitcher_name}' (normalized: '{pitcher_clean}')")
        logger.info(f"📋 Available pitchers: {[clean_player_name(name) for name in all_pitcher_names[:10]]}")
        return None
    
    def _find_team_batters(self, team_abbr: str) -> List[Dict[str, Any]]:
        """Find all batters for a given team."""
        batters = []
        
        for pid, pdata in self.master_player_data.items():
            roster_info = pdata.get('roster_info', {})
            if (roster_info.get('type') == 'hitter' and 
                roster_info.get('team', '').upper() == team_abbr.upper()):
                
                batters.append({
                    'batter_id': pid,
                    'name': roster_info.get('fullName', f"Player_{pid}"),  # FIXED: Use roster fullName, not CSV-derived
                    'team': team_abbr.upper(),
                    'bats': roster_info.get('bats', 'R')
                })
        
        return batters
    
    def _get_recent_batter_performance(self, batter_id: str) -> Optional[Dict[str, Any]]:
        """Get recent performance stats for a batter using comprehensive lookup chain."""
        from data_loader import get_last_n_games_performance
        
        # Get batter info
        batter_data = self.master_player_data.get(batter_id, {})
        roster_info = batter_data.get('roster_info', {})
        
        if not roster_info:
            logger.warning(f"No roster info found for batter {batter_id}")
            return None
        
        # Use the comprehensive lookup chain with the batter's fullName
        # CRITICAL: Prioritize roster fullName over CSV-derived fullName_resolved
        player_full_name = roster_info.get('fullName') or roster_info.get('fullName_resolved', '')
        if not player_full_name:
            logger.warning(f"No fullName found for batter {batter_id}")
            return None
        
        try:
            # Call the comprehensive lookup chain with correct parameter order
            # Function signature: get_last_n_games_performance(player_full_name_resolved, daily_data, roster_data_list, n_games=7)
            logger.info(f"🔍 COMPREHENSIVE LOOKUP: Searching for '{player_full_name}' in daily data...")
            logger.info(f"📊 Available data: {len(self.daily_game_data)} daily dates, {len(self.roster_data)} roster entries")
            
            last_games, at_bats = get_last_n_games_performance(
                player_full_name, self.daily_game_data, self.roster_data, 7
            )
            
            if not last_games:
                logger.debug(f"No recent games found for {player_full_name} - will use FALLBACK")
                return None
            
            # Calculate recent performance from actual games
            total_ab = sum(game.get('AB', 0) for game in last_games)
            total_hits = sum(game.get('H', 0) for game in last_games)
            total_hrs = sum(game.get('HR', 0) for game in last_games)
            total_bb = sum(game.get('BB', 0) for game in last_games)
            total_k = sum(game.get('K', 0) for game in last_games)
            
            # Calculate derived stats
            hit_rate = total_hits / total_ab if total_ab > 0 else 0
            hr_per_ab = total_hrs / total_ab if total_ab > 0 else 0
            total_pa = total_ab + total_bb  # Simplified PA calculation
            hr_per_pa = total_hrs / total_pa if total_pa > 0 else 0
            
            # USE EXACT PINHEAD-CLAUDE CALCULATION
            from pinhead_ported_scoring import calculate_recent_trends_exact_pinhead
            
            # This returns the EXACT same structure as Pinhead-Claude analyzer.py
            pinhead_trends = calculate_recent_trends_exact_pinhead(last_games)
            trend_direction = pinhead_trends.get('trend_direction', 'stable')
            trend_magnitude = pinhead_trends.get('trend_magnitude', 0.0)
            recent_avg = pinhead_trends.get('avg_avg', hit_rate)  # EXACT Pinhead-Claude avg_avg calculation
            logger.info(f"✅ RECENT PERFORMANCE SUCCESS: {player_full_name} - {len(last_games)} games, {total_hits}/{total_ab} (Recent Avg: {recent_avg:.3f}, HR Rate: {hr_per_ab:.1%})")
            logger.info(f"📊 DETAILED STATS: AB Due: {total_ab - total_hits}, PA: {total_pa}, BB: {total_bb}, K: {total_k}")
            
            return {
                'last_7_games': last_games,  # Include the actual games data
                'total_games': len(last_games),
                'total_ab': total_ab,
                'total_hits': total_hits,
                'total_hrs': total_hrs,
                'total_bb': total_bb,
                'total_k': total_k,
                'total_pa_approx': total_pa,
                'hit_rate': hit_rate,
                'hr_per_pa': hr_per_pa,
                'avg_avg': recent_avg,  # EXACT Pinhead-Claude avg_avg calculation
                'hr_rate': pinhead_trends.get('hr_rate', hr_per_ab),  # EXACT Pinhead-Claude hr_rate (AB-based decimal)
                'trend_direction': trend_direction,  # EXACT Pinhead-Claude trend calculation
                'trend_magnitude': trend_magnitude,  # EXACT Pinhead-Claude magnitude
                'pinhead_trends_full': pinhead_trends,  # Include full Pinhead-Claude trends for debugging
                'data_source': 'pinhead_claude_ported'  # Mark as using ported Pinhead-Claude logic
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive lookup for {player_full_name}: {e}")
            return None
    
    def _get_pitcher_trend_analysis(self, pitcher_id: str, pitcher_name: str) -> Dict[str, Any]:
        """
        PORTED FROM PINHEAD-CLAUDE: Use proven pitcher trend calculation
        """
        from pinhead_ported_functions import get_last_n_games_performance_pitcher_ported, calculate_recent_trends_pitcher_ported
        
        try:
            # Get pitcher data from master_player_data
            pitcher_master_data = self.master_player_data.get(str(pitcher_id))
            if not pitcher_master_data:
                logger.warning(f"⚠️ PITCHER TREND: {pitcher_name} not found in master data - using defaults")
                return {
                    'trend_direction': 'stable',
                    'trend_magnitude': 0.0,
                    'data_source': 'none',
                    'p_games_found': 0
                }
            
            pitcher_roster_info = pitcher_master_data.get('roster_info', {})
            pitcher_full_name = pitcher_roster_info.get('fullName') or pitcher_name
            
            # USE PORTED PINHEAD-CLAUDE FUNCTIONS
            last_games, _ = get_last_n_games_performance_pitcher_ported(
                pitcher_full_name, self.daily_game_data, self.roster_data, 7
            )
            
            if not last_games:
                logger.warning(f"⚠️ PITCHER TREND: {pitcher_name} not found in roster data - using defaults")
                return {
                    'trend_direction': 'stable',
                    'trend_magnitude': 0.0,
                    'data_source': 'none',
                    'p_games_found': 0
                }
            
            # USE PORTED PINHEAD-CLAUDE TREND CALCULATION
            pitcher_trends = calculate_recent_trends_pitcher_ported(last_games)
            
            trend_direction = pitcher_trends.get('trend_direction', 'stable')
            logger.info(f"📈 PITCHER TREND: {pitcher_name} - Direction: {trend_direction}")
            
            return {
                'trend_direction': trend_direction,
                'trend_magnitude': pitcher_trends.get('trend_magnitude', 0.0),
                'data_source': 'pinhead_claude_ported',
                'p_games_found': len(last_games),
                'recent_era': pitcher_trends.get('trend_recent_val', 0.0),
                'early_era': pitcher_trends.get('trend_early_val', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error in ported pitcher trend calculation for {pitcher_name}: {e}")
            return {
                'trend_direction': 'stable',
                'trend_magnitude': 0.0,
                'data_source': 'error',
                'p_games_found': 0
            }
    
    def _calculate_comprehensive_pitcher_stats(self, pitcher_id: str, pitcher_name: str) -> Dict[str, Any]:
        """Calculate comprehensive pitcher home game stats from ALL available daily data"""
        try:
            pitcher_data = self.master_player_data.get(pitcher_id, {})
            pitcher_roster_info = pitcher_data.get('roster_info', {})
            
            logger.info(f"🏠 Calculating home stats for: {pitcher_name} (ID: {pitcher_id})")
            roster_short_name = pitcher_roster_info.get('name', '')
            roster_full_name = pitcher_roster_info.get('fullName', '')
            
            # Search through ALL daily game data for this pitcher
            all_home_games = []
            all_away_games = []
            total_pitcher_entries = 0
            
            for date_key, date_data in self.daily_game_data.items():
                if not isinstance(date_data, dict):
                    continue
                    
                # Get games for this date
                games = date_data.get('games', [])
                players = date_data.get('players', [])
                
                # Create game lookup by gameId (which matches originalId in games)
                game_lookup = {}
                for game in games:
                    if isinstance(game, dict) and 'originalId' in game:
                        game_lookup[str(game['originalId'])] = game
                
                # Check pitcher stats in players array
                for player in players:
                    if not isinstance(player, dict):
                        continue
                        
                    # Match pitcher by name and type
                    player_name = player.get('name', '').strip()
                    player_type = player.get('playerType', '').strip()
                    
                    if player_type == 'pitcher':
                        total_pitcher_entries += 1
                    
                    # Create multiple name variants for matching
                    csv_format_name = ""
                    if roster_full_name and ' ' in roster_full_name:
                        name_parts = roster_full_name.split(' ')
                        if len(name_parts) >= 2:
                            csv_format_name = f"{name_parts[-1]}, {name_parts[0]}"
                    
                    pitcher_names_to_check = [
                        pitcher_name.lower(),
                        roster_short_name.lower(),
                        roster_full_name.lower(),
                        csv_format_name.lower(),
                    ]
                    
                    name_matches = any(
                        player_name.lower() == name for name in pitcher_names_to_check if name
                    )
                    
                    if (player_type == 'pitcher' and 
                        (name_matches or str(player.get('player_id', '')) == str(pitcher_id))):
                        
                        logger.debug(f"✅ Found pitcher match: '{player_name}' on {date_key}")
                        
                        # Get the game info for this player
                        game_id = player.get('gameId')
                        game_info = game_lookup.get(game_id, {})
                        
                        if game_info:
                            # Determine if this is a home game for the pitcher
                            pitcher_team = player.get('team', '').upper()
                            home_team = game_info.get('homeTeam', '').upper()
                            is_home = pitcher_team == home_team
                            
                            # Extract pitcher stats
                            try:
                                game_stats = {
                                    'h': int(player.get('H', 0)),
                                    'hr': int(player.get('HR', 0)), 
                                    'k': int(player.get('K', 0)),
                                    'ip': float(player.get('IP', 0)),
                                    'r': int(player.get('R', 0)),
                                    'er': int(player.get('ER', 0)),
                                    'bb': int(player.get('BB', 0)),
                                    'date': date_key,
                                    'team': pitcher_team
                                }
                                
                                if is_home:
                                    all_home_games.append(game_stats)
                                    logger.debug(f"🏠 Home game: {date_key}, H={game_stats['h']}, HR={game_stats['hr']}, K={game_stats['k']}")
                                else:
                                    all_away_games.append(game_stats)
                                    
                            except (ValueError, TypeError) as e:
                                logger.warning(f"⚠️ Error parsing stats for {player_name} on {date_key}: {e}")
                                continue
            
            # Calculate comprehensive home stats
            home_stats = {
                'total_games': len(all_home_games),
                'total_h': sum(g['h'] for g in all_home_games),
                'total_hr': sum(g['hr'] for g in all_home_games),
                'total_k': sum(g['k'] for g in all_home_games),
                'total_ip': sum(g['ip'] for g in all_home_games),
            }
            
            logger.info(f"🏠 HOME STATS: {pitcher_name} - {home_stats['total_games']} games, {home_stats['total_h']} H, {home_stats['total_hr']} HR, {home_stats['total_k']} K")
            
            return {
                'pitcher_home_h_total': home_stats['total_h'],
                'pitcher_home_hr_total': home_stats['total_hr'],
                'pitcher_home_k_total': home_stats['total_k'],
                'pitcher_home_games': home_stats['total_games'],
                'comprehensive_data_available': len(all_home_games) > 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating comprehensive pitcher stats: {e}")
            return {
                'pitcher_home_h_total': 0,
                'pitcher_home_hr_total': 0,
                'pitcher_home_k_total': 0,
                'pitcher_home_games': 0,
                'comprehensive_data_available': False
            }
    
    def _calculate_comprehensive_hitter_stats(self, batter_id: str, batter_name: str) -> Dict[str, Any]:
        """Calculate comprehensive hitter stats from ALL available daily data - similar to pitcher stats"""
        try:
            batter_data = self.master_player_data.get(batter_id, {})
            batter_roster_info = batter_data.get('roster_info', {})
            
            logger.info(f"🏏 Calculating comprehensive hitter stats for: {batter_name} (ID: {batter_id})")
            roster_short_name = batter_roster_info.get('name', '')  # "P. Alonso"
            roster_full_name = batter_roster_info.get('fullName', '')  # "Pete Alonso"
            
            # Search through ALL daily game data for this hitter (same logic as pitcher)
            all_games = []
            total_hitter_entries = 0
            last_hr_game_index = -1  # Track position of last HR
            
            for date_key, date_data in self.daily_game_data.items():
                if not isinstance(date_data, dict):
                    continue
                    
                # Get players for this date
                players = date_data.get('players', [])
                
                # Check hitter stats in players array
                for player in players:
                    if not isinstance(player, dict):
                        continue
                        
                    # Match hitter by name and type
                    player_name = player.get('name', '').strip()
                    player_type = player.get('playerType', '').strip()
                    
                    if player_type == 'hitter':
                        total_hitter_entries += 1
                    
                    # Create multiple name variants for matching (enhanced to match pitcher logic)
                    csv_format_name = ""
                    initial_lastname_format = ""
                    if roster_full_name and ' ' in roster_full_name:
                        name_parts = roster_full_name.split(' ')
                        if len(name_parts) >= 2:
                            csv_format_name = f"{name_parts[-1]}, {name_parts[0]}"  # "Alonso, Pete"
                            # CRITICAL FIX: Create "A. Lastname" format that daily JSON files use
                            initial_lastname_format = f"{name_parts[0][0]}. {name_parts[-1]}"  # "P. Alonso"
                    
                    hitter_names_to_check = [
                        batter_name.lower(),  # API request name
                        roster_short_name.lower(),  # "p. alonso" from roster
                        roster_full_name.lower(),  # "pete alonso" from roster
                        csv_format_name.lower(),  # "alonso, pete" (CSV format)
                        initial_lastname_format.lower(),  # "p. alonso" (daily JSON format) - CRITICAL FIX
                    ]
                    
                    # ENHANCED DEBUG: Log name matching attempts
                    name_matches = any(
                        player_name.lower() == name for name in hitter_names_to_check if name
                    )
                    
                    if player_type == 'hitter' and any(hitter_names_to_check):
                        logger.debug(f"🔍 HITTER NAME MATCH: Checking '{player_name}' against {[n for n in hitter_names_to_check if n]} -> Match: {name_matches}")
                    
                    if (player_type == 'hitter' and 
                        (name_matches or str(player.get('player_id', '')) == str(batter_id))):
                        
                        logger.debug(f"✅ Found hitter match: '{player_name}' on {date_key}")
                        
                        # Extract hitter stats using correct field names
                        try:
                            game_stats = {
                                'ab': int(player.get('AB', 0)),
                                'h': int(player.get('H', 0)),
                                'hr': int(player.get('HR', 0)),
                                '2b': int(player.get('2B', 0)),
                                '3b': int(player.get('3B', 0)),
                                'rbi': int(player.get('RBI', 0)),
                                'bb': int(player.get('BB', 0)),
                                'k': int(player.get('K', 0)),
                                'avg': float(player.get('AVG', 0)) if player.get('AVG') else 0,
                                'obp': float(player.get('OBP', 0)) if player.get('OBP') else 0,
                                'slg': float(player.get('SLG', 0)) if player.get('SLG') else 0,
                                'date': date_key,
                                'team': player.get('team', '').upper()
                            }
                            
                            all_games.append(game_stats)
                            
                            # Track last HR for "H since HR" calculation
                            if game_stats['hr'] > 0:
                                last_hr_game_index = len(all_games) - 1
                            
                            logger.debug(f"🏏 Hitter game: {date_key}, H={game_stats['h']}, HR={game_stats['hr']}, SLG={game_stats['slg']}")
                                
                        except (ValueError, TypeError) as e:
                            logger.warning(f"⚠️ Error parsing hitter stats for {player_name} on {date_key}: {e}")
                            continue
            
            # Sort games by date to ensure chronological order
            all_games.sort(key=lambda x: x['date'])
            
            # Calculate comprehensive hitter stats
            if len(all_games) == 0:
                logger.warning(f"⚠️ No hitter game data found for {batter_name}")
                return {
                    'hitter_slg': 0,
                    'h_since_hr': 0,
                    'hitter_total_games': 0,
                    'hitter_total_ab': 0,
                    'hitter_total_h': 0,
                    'hitter_total_hr': 0,
                    'heating_up': 0,
                    'cold': 0,
                    'comprehensive_data_available': False
                }
            
            # Basic totals
            total_games = len(all_games)
            total_ab = sum(g['ab'] for g in all_games)
            total_h = sum(g['h'] for g in all_games)
            total_hr = sum(g['hr'] for g in all_games)
            total_2b = sum(g['2b'] for g in all_games)
            total_3b = sum(g['3b'] for g in all_games)
            total_bb = sum(g['bb'] for g in all_games)
            total_k = sum(g['k'] for g in all_games)
            
            # Calculate slugging percentage (total bases / at bats)
            singles = total_h - total_2b - total_3b - total_hr
            total_bases = singles + (total_2b * 2) + (total_3b * 3) + (total_hr * 4)
            hitter_slg = total_bases / total_ab if total_ab > 0 else 0
            
            # Calculate hits since last HR
            h_since_hr = 0
            if last_hr_game_index >= 0:
                # Count hits in games after the last HR
                for i in range(last_hr_game_index + 1, len(all_games)):
                    h_since_hr += all_games[i]['h']
            else:
                # No HR found, count all hits
                h_since_hr = total_h
            
            # Calculate heating up / cold factors (recent 10 games vs previous 10 games)
            heating_up = 0
            cold = 0
            if len(all_games) >= 20:  # Need at least 20 games for comparison
                recent_10 = all_games[-10:]
                previous_10 = all_games[-20:-10]
                
                recent_avg = sum(g['h'] for g in recent_10) / sum(g['ab'] for g in recent_10) if sum(g['ab'] for g in recent_10) > 0 else 0
                previous_avg = sum(g['h'] for g in previous_10) / sum(g['ab'] for g in previous_10) if sum(g['ab'] for g in previous_10) > 0 else 0
                
                avg_diff = recent_avg - previous_avg
                if avg_diff > 0.05:  # Significant improvement
                    heating_up = min(10, avg_diff * 100)  # Scale to 0-10
                elif avg_diff < -0.05:  # Significant decline
                    cold = min(10, abs(avg_diff) * 100)  # Scale to 0-10
            
            logger.info(f"🏏 HITTER STATS: {batter_name} - {total_games} games, SLG: {hitter_slg:.3f}, H since HR: {h_since_hr}, Heating up: {heating_up:.1f}")
            
            return {
                'hitter_slg': round(hitter_slg, 3),
                'h_since_hr': h_since_hr,
                'hitter_total_games': total_games,
                'hitter_total_ab': total_ab,
                'hitter_total_h': total_h,
                'hitter_total_hr': total_hr,
                'heating_up': round(heating_up, 1),
                'cold': round(cold, 1),
                'comprehensive_data_available': True
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating comprehensive hitter stats: {e}")
            return {
                'hitter_slg': 0,
                'h_since_hr': 0,
                'hitter_total_games': 0,
                'hitter_total_ab': 0,
                'hitter_total_h': 0,
                'hitter_total_hr': 0,
                'heating_up': 0,
                'cold': 0,
                'comprehensive_data_available': False
            }
    
    def _calculate_confidence_distribution(self, analyses: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of confidence levels."""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for analysis in analyses:
            confidence = analysis.get('confidence', 0)
            if confidence >= 0.7:
                distribution['high'] += 1
            elif confidence >= 0.4:
                distribution['medium'] += 1
            else:
                distribution['low'] += 1
        
        return distribution
    
    def _assess_missing_data_impact(self, avg_confidence: float, primary_data_source: str) -> Dict[str, Any]:
        """Assess the impact of missing data on analysis quality."""
        impact_assessment = {
            'severity': 'low',
            'description': 'Full pitcher data available for most analyses',
            'recommendations': []
        }
        
        if primary_data_source == 'league_average':
            impact_assessment['severity'] = 'high'
            impact_assessment['description'] = 'Most analyses rely on league average fallbacks due to missing pitcher data'
            impact_assessment['recommendations'] = [
                'Consider using alternative data sources for pitcher information',
                'Implement pitcher historical data backfill',
                'Use team-based pitching profiles when available'
            ]
        elif primary_data_source == 'team_based':
            impact_assessment['severity'] = 'medium'
            impact_assessment['description'] = 'Analyses use team-based estimates due to limited individual pitcher data'
            impact_assessment['recommendations'] = [
                'Enhance pitcher-specific data collection',
                'Validate team-based estimates against available individual data'
            ]
        elif primary_data_source == 'pitcher_partial':
            impact_assessment['severity'] = 'low'
            impact_assessment['description'] = 'Partial pitcher data available, supplemented with league averages'
            impact_assessment['recommendations'] = [
                'Monitor data completeness for key pitchers',
                'Consider historical data to fill gaps'
            ]
        
        if avg_confidence < 0.5:
            impact_assessment['severity'] = max(impact_assessment['severity'], 'medium')
            impact_assessment['recommendations'].append('Consider displaying confidence warnings to users')
        
        return impact_assessment
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get statistics about analyses performed."""
        total = self.analysis_stats['total_analyses']
        if total == 0:
            return {'message': 'No analyses performed yet'}
        
        return {
            'total_analyses': total,
            'success_rate': round((total - self.analysis_stats['failed_analyses']) / total * 100, 1),
            'data_quality_breakdown': {
                'full_data_percentage': round(self.analysis_stats['full_data_analyses'] / total * 100, 1),
                'partial_data_percentage': round(self.analysis_stats['partial_data_analyses'] / total * 100, 1),
                'team_based_percentage': round(self.analysis_stats['team_based_analyses'] / total * 100, 1),
                'league_average_percentage': round(self.analysis_stats['league_average_analyses'] / total * 100, 1)
            },
            'recommendations': self._generate_data_quality_recommendations()
        }
    
    def _generate_data_quality_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis statistics."""
        recommendations = []
        total = self.analysis_stats['total_analyses']
        
        if total == 0:
            return recommendations
        
        league_avg_pct = self.analysis_stats['league_average_analyses'] / total
        team_based_pct = self.analysis_stats['team_based_analyses'] / total
        failed_pct = self.analysis_stats['failed_analyses'] / total
        
        if league_avg_pct > 0.5:
            recommendations.append("High reliance on league averages detected - consider improving pitcher data collection")
        
        if team_based_pct > 0.3:
            recommendations.append("Frequent use of team-based estimates - validate against individual pitcher performance")
        
        if failed_pct > 0.1:
            recommendations.append("Analysis failure rate above threshold - investigate data quality issues")
        
        if self.analysis_stats['full_data_analyses'] / total < 0.3:
            recommendations.append("Low percentage of full-data analyses - prioritize complete pitcher arsenal data")
        
        return recommendations

def create_enhanced_analysis_report(analysis_result: Dict[str, Any]) -> str:
    """
    Create a formatted report explaining the analysis quality and missing data handling.
    """
    if not analysis_result.get('success', False):
        return f"Analysis failed: {analysis_result.get('error', 'Unknown error')}"
    
    report_lines = []
    report_lines.append(f"=== Enhanced Analysis Report ===")
    report_lines.append(f"Pitcher: {analysis_result['pitcher_name']}")
    report_lines.append(f"vs Team: {analysis_result['team']}")
    report_lines.append(f"Batters Analyzed: {analysis_result['total_batters_analyzed']}")
    report_lines.append(f"Overall Reliability: {analysis_result['reliability'].upper()}")
    report_lines.append(f"Average Confidence: {analysis_result['average_confidence']:.1%}")
    report_lines.append(f"Primary Data Source: {analysis_result['primary_data_source'].replace('_', ' ').title()}")
    
    if 'data_quality_breakdown' in analysis_result:
        quality = analysis_result['data_quality_breakdown']
        report_lines.append("\n--- Data Quality Breakdown ---")
        
        analysis_summary = quality['analysis_summary']
        if analysis_summary['full_pitcher_data'] > 0:
            report_lines.append(f"✓ Full pitcher data: {analysis_summary['full_pitcher_data']} analyses")
        if analysis_summary['partial_pitcher_data'] > 0:
            report_lines.append(f"~ Partial pitcher data: {analysis_summary['partial_pitcher_data']} analyses")
        if analysis_summary['team_based_estimates'] > 0:
            report_lines.append(f"◦ Team-based estimates: {analysis_summary['team_based_estimates']} analyses")
        if analysis_summary['league_average_fallbacks'] > 0:
            report_lines.append(f"◦ League average fallbacks: {analysis_summary['league_average_fallbacks']} analyses")
        
        if 'missing_data_impact' in quality:
            impact = quality['missing_data_impact']
            report_lines.append(f"\n--- Missing Data Impact ---")
            report_lines.append(f"Severity: {impact['severity'].upper()}")
            report_lines.append(f"Description: {impact['description']}")
            
            if impact['recommendations']:
                report_lines.append("Recommendations:")
                for rec in impact['recommendations']:
                    report_lines.append(f"  • {rec}")
    
    # Top predictions summary
    if analysis_result.get('predictions'):
        report_lines.append("\n--- Top Predictions ---")
        top_predictions = analysis_result['predictions'][:5]
        for i, pred in enumerate(top_predictions, 1):
            confidence_indicator = "🟢" if pred.get('confidence', 0) >= 0.7 else "🟡" if pred.get('confidence', 0) >= 0.4 else "🔴"
            report_lines.append(
                f"{i}. {pred['batter_name']} - Score: {pred['score']:.1f} "
                f"({pred.get('confidence', 0):.1%} confidence {confidence_indicator})"
            )
    
    return "\n".join(report_lines)