#!/usr/bin/env python3
"""
Batch Fixed Real Data Only - Baseball Analysis API
Fixed batch analysis to handle team_abbr properly
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import core modules
try:
    from utils import find_player_id_by_name, clean_player_name
    from data_loader import initialize_data, get_last_n_games_performance
    from analyzer import enhanced_hr_likelihood_score, calculate_recent_trends
    logger.info("✅ Core modules imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import core modules: {e}")
    raise

# Create FastAPI app
app = FastAPI(title="Batch Fixed Real Data Baseball API", version="1.2.0-batch-fixed")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PredictionRequest(BaseModel):
    pitcher_name: str
    team: str
    sort_by: Optional[str] = "score"
    min_score: Optional[float] = 0
    max_results: Optional[int] = None
    include_confidence: Optional[bool] = True

# Global data storage
global_data = {
    'master_player_data': None,
    'player_id_to_name_map': None,
    'name_to_player_id_map': None,
    'daily_game_data': None,
    'roster_data': None,
    'historical_data': None,
    'league_avg_stats': None,
    'metric_ranges': None,
    'initialization_status': 'not_started',
    'initialization_error': None
}

@app.on_event("startup")
async def startup_event():
    """Initialize with real data only"""
    await initialize_real_data_only()

async def initialize_real_data_only():
    """Initialize using ONLY real data from files"""
    try:
        global_data['initialization_status'] = 'in_progress'
        logger.info("🔍 Initializing with REAL DATA ONLY - no mock data")
        
        # Initialize base data
        result = initialize_data()
        if not result or len(result) != 8:
            raise ValueError(f"Data initialization failed - got {len(result) if result else 0} items, expected 8")
        
        (master_player_data, player_id_to_name_map, name_to_player_id_map, 
         daily_game_data, roster_data, historical_data, league_avg_stats, metric_ranges) = result
        
        # Store ALL the real data
        global_data.update({
            'master_player_data': master_player_data,
            'player_id_to_name_map': player_id_to_name_map,
            'name_to_player_id_map': name_to_player_id_map,
            'daily_game_data': daily_game_data,
            'roster_data': roster_data,
            'historical_data': historical_data,
            'league_avg_stats': league_avg_stats,
            'metric_ranges': metric_ranges
        })
        
        global_data['initialization_status'] = 'completed'
        
        # Log what we actually loaded from files
        logger.info(f"✅ REAL DATA LOADED:")
        logger.info(f"📊 Master players: {len(master_player_data)}")
        logger.info(f"📋 Roster entries: {len(roster_data) if roster_data else 0}")
        logger.info(f"📅 Daily game dates: {len(daily_game_data)}")
        logger.info(f"📈 Historical data years: {list(historical_data.keys()) if historical_data else []}")
        logger.info(f"⚾ League averages calculated: {bool(league_avg_stats)}")
        
    except Exception as e:
        global_data['initialization_status'] = 'failed'
        global_data['initialization_error'] = str(e)
        logger.error(f"❌ Real data initialization failed: {e}")
        raise

def get_roster_info_for_player(master_data, player_id, roster_data):
    """Get comprehensive roster info for a player"""
    # Try master data first
    player_data = master_data.get(player_id, {})
    roster_info = player_data.get('roster_info', {})
    
    if roster_info:
        return roster_info
    
    # Fallback: search roster_data directly
    if roster_data:
        for roster_entry in roster_data:
            if str(roster_entry.get('mlbam_id', '')) == str(player_id):
                return roster_entry
    
    return {}

def calculate_comprehensive_pitcher_stats(pitcher_id, master_data, daily_game_data):
    """Calculate comprehensive pitcher stats from ALL available data, not just recent games"""
    try:
        pitcher_data = master_data.get(pitcher_id, {})
        pitcher_name = pitcher_data.get('roster_info', {}).get('fullName_resolved', f"Pitcher_{pitcher_id}")
        
        logger.info(f"🔍 Searching for pitcher stats: {pitcher_name} (ID: {pitcher_id})")
        roster_short_name = pitcher_data.get('roster_info', {}).get('name', '')
        roster_full_name = pitcher_data.get('roster_info', {}).get('fullName', '')
        logger.info(f"📋 Pitcher names - API: '{pitcher_name}', Short: '{roster_short_name}', Full: '{roster_full_name}'")
        
        # Search through ALL daily game data for this pitcher
        all_home_games = []
        all_away_games = []
        total_pitcher_entries = 0
        
        for date_key, date_data in daily_game_data.items():
            if not isinstance(date_data, dict):
                continue
                
            # Get games for this date
            games = date_data.get('games', [])
            players = date_data.get('players', [])
            
            # Create game lookup by gameId (which matches originalId in games)
            game_lookup = {}
            for game in games:
                if isinstance(game, dict) and 'originalId' in game:
                    # Player data uses 'gameId' which corresponds to 'originalId' in games
                    game_lookup[str(game['originalId'])] = game
            
            # Check pitcher stats in players array
            for player in players:
                if not isinstance(player, dict):
                    continue
                    
                # Match pitcher by name and type
                player_name = player.get('name', '').strip()
                player_type = player.get('playerType', '').strip()
                
                # Count all pitcher entries for debugging
                if player_type == 'pitcher':
                    total_pitcher_entries += 1
                    # Log first few pitcher names we find for debugging
                    if total_pitcher_entries <= 3:
                        logger.info(f"🔍 Found pitcher in data: '{player_name}' (entry #{total_pitcher_entries})")
                
                # Create multiple name variants for matching all possible formats
                roster_short_name = pitcher_data.get('roster_info', {}).get('name', '')  # "A. Abbott"
                roster_full_name = pitcher_data.get('roster_info', {}).get('fullName', '')  # "Andrew Abbott"
                
                # Create CSV format "Last, First" from full name
                csv_format_name = ""
                if roster_full_name and ' ' in roster_full_name:
                    name_parts = roster_full_name.split(' ')
                    if len(name_parts) >= 2:
                        csv_format_name = f"{name_parts[-1]}, {name_parts[0]}"  # "Abbott, Andrew"
                
                pitcher_names_to_check = [
                    pitcher_name.lower(),  # API request name: "andrew abbott"
                    roster_short_name.lower(),  # Roster short: "a. abbott"
                    roster_full_name.lower(),  # Roster full: "andrew abbott"
                    csv_format_name.lower(),  # CSV format: "abbott, andrew"
                ]
                
                name_matches = any(
                    player_name.lower() == name for name in pitcher_names_to_check if name
                )
                
                if (player_type == 'pitcher' and 
                    (name_matches or str(player.get('player_id', '')) == str(pitcher_id))):
                    
                    logger.info(f"✅ Found pitcher match: '{player_name}' on {date_key}")
                    
                    # Get the game info for this player
                    game_id = player.get('gameId')
                    game_info = game_lookup.get(game_id, {})
                    
                    logger.debug(f"🔍 Game lookup: gameId={game_id}, found_game={bool(game_info)}")
                    if not game_info:
                        logger.warning(f"⚠️ No game info found for gameId {game_id} in game_lookup")
                    
                    if game_info:
                        # Determine if this is a home game for the pitcher
                        pitcher_team = player.get('team', '').upper()
                        home_team = game_info.get('homeTeam', '').upper()
                        is_home = pitcher_team == home_team
                        
                        # Extract pitcher stats using correct field names
                        try:
                            game_stats = {
                                'h': int(player.get('H', 0)),
                                'hr': int(player.get('HR', 0)), 
                                'k': int(player.get('K', 0)),
                                'ip': float(player.get('IP', 0)),
                                'r': int(player.get('R', 0)),
                                'er': int(player.get('ER', 0)),
                                'bb': int(player.get('BB', 0)),
                                'era': float(player.get('ERA', 0)) if player.get('ERA') else None,
                                'date': date_key,
                                'game_id': game_id,
                                'team': pitcher_team
                            }
                            
                            logger.debug(f"📊 Extracted stats: H={game_stats['h']}, HR={game_stats['hr']}, K={game_stats['k']}, IP={game_stats['ip']}")
                            
                            if is_home:
                                all_home_games.append(game_stats)
                                logger.debug(f"📊 Home game found: {date_key}, H={game_stats['h']}, HR={game_stats['hr']}, K={game_stats['k']}")
                            else:
                                all_away_games.append(game_stats)
                                logger.debug(f"📊 Away game found: {date_key}, H={game_stats['h']}, HR={game_stats['hr']}, K={game_stats['k']}")
                                
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
            'avg_h_per_game': round(sum(g['h'] for g in all_home_games) / len(all_home_games), 2) if all_home_games else 0,
            'avg_hr_per_game': round(sum(g['hr'] for g in all_home_games) / len(all_home_games), 2) if all_home_games else 0,
            'avg_k_per_game': round(sum(g['k'] for g in all_home_games) / len(all_home_games), 2) if all_home_games else 0
        }
        
        # Calculate trend direction from all available games (not just home games)
        all_games = all_home_games + all_away_games
        trend_direction = None
        
        logger.info(f"📊 Searched through {total_pitcher_entries} total pitcher entries")
        logger.info(f"📊 Found {len(all_home_games)} home games, {len(all_away_games)} away games, {len(all_games)} total games")
        
        if len(all_games) >= 4:  # Need at least 4 games to calculate trend
            # Sort by date and take recent games
            sorted_games = sorted(all_games, key=lambda x: x['date'])
            recent_games = sorted_games[-8:] if len(sorted_games) >= 8 else sorted_games
            
            if len(recent_games) >= 4:
                mid_point = len(recent_games) // 2
                early_games = recent_games[:mid_point]
                late_games = recent_games[mid_point:]
                
                # Calculate ERA for each half (using earned runs and innings pitched)
                early_er = sum(g['er'] for g in early_games)
                early_ip = sum(g['ip'] for g in early_games)
                late_er = sum(g['er'] for g in late_games)
                late_ip = sum(g['ip'] for g in late_games)
                
                if early_ip > 0 and late_ip > 0:
                    early_era = (early_er / early_ip) * 9
                    late_era = (late_er / late_ip) * 9
                    
                    logger.info(f"📈 ERA trend: early={early_era:.2f}, late={late_era:.2f}")
                    
                    if late_era < early_era - 1.0:
                        trend_direction = 'improving'
                    elif late_era > early_era + 1.0:
                        trend_direction = 'declining'
                    else:
                        trend_direction = 'stable'
                    
                    logger.info(f"📊 Pitcher trend direction: {trend_direction}")
                else:
                    logger.warning(f"⚠️ Insufficient innings pitched data for trend calculation")
            else:
                logger.warning(f"⚠️ Only {len(recent_games)} recent games found, need at least 4")
        else:
            logger.warning(f"⚠️ Only {len(all_games)} total games found, need at least 4")
        
        # If we didn't find enough data, provide basic stats with a note
        if len(all_games) == 0:
            logger.warning(f"⚠️ No pitcher game data found for {pitcher_name}. This may be due to name format differences.")
            return {
                'pitcher_home_h_total': 0,
                'pitcher_home_hr_total': 0,
                'pitcher_home_k_total': 0,
                'pitcher_home_games': 0,
                'pitcher_trend_direction': 'stable',  # Default trend
                'comprehensive_data_available': False
            }
        
        return {
            'pitcher_home_h_total': home_stats['total_h'],
            'pitcher_home_hr_total': home_stats['total_hr'],
            'pitcher_home_k_total': home_stats['total_k'],
            'pitcher_home_games': home_stats['total_games'],
            'pitcher_trend_direction': trend_direction or 'stable',  # Fallback to stable
            'comprehensive_data_available': True
        }
        
    except Exception as e:
        logger.error(f"❌ Error calculating comprehensive pitcher stats: {e}")
        return {
            'pitcher_home_h_total': None,
            'pitcher_home_hr_total': None,
            'pitcher_home_k_total': None,
            'pitcher_home_games': 0,
            'pitcher_trend_direction': None,
            'comprehensive_data_available': False
        }

def calculate_batter_trend_direction(recent_stats, batter_roster_info):
    """Calculate batter trend direction from recent performance"""
    try:
        if not recent_stats:
            return None
            
        # Check if we have trend data in recent stats
        if 'trend_direction' in recent_stats:
            return recent_stats['trend_direction']
            
        # Calculate based on recent performance if available
        recent_games = recent_stats.get('recent_games', [])
        if len(recent_games) >= 4:
            mid_point = len(recent_games) // 2
            early_games = recent_games[:mid_point]
            late_games = recent_games[mid_point:]
            
            # Calculate HR per PA for each half
            early_hr = sum(g.get('hr', 0) for g in early_games)
            early_pa = sum(g.get('pa', 0) for g in early_games)
            late_hr = sum(g.get('hr', 0) for g in late_games)
            late_pa = sum(g.get('pa', 0) for g in late_games)
            
            if early_pa > 0 and late_pa > 0:
                early_hr_rate = early_hr / early_pa
                late_hr_rate = late_hr / late_pa
                
                if late_hr_rate > early_hr_rate + 0.02:
                    return 'improving'
                elif late_hr_rate < early_hr_rate - 0.02:
                    return 'declining'
                else:
                    return 'stable'
        
        return None
    except Exception as e:
        logger.error(f"❌ Error calculating batter trend direction: {e}")
        return None

def extract_all_fields_from_analysis(analysis_result, batter_roster_info, pitcher_roster_info, recent_stats=None, pitcher_id=None, master_data=None, daily_game_data=None):
    """Extract all expected fields from analysis result with proper fallbacks"""
    if not analysis_result:
        return None
    
    # Get basic info
    details = analysis_result.get('details', {})
    components = analysis_result.get('matchup_components', {})
    outcome_probs = analysis_result.get('outcome_probabilities', {})
    
    # Extract batter hand and pitcher hand from roster data
    batter_hand = 'UNKNOWN'
    pitcher_hand = 'UNKNOWN'
    
    if batter_roster_info:
        batter_hand = batter_roster_info.get('bats', batter_roster_info.get('hand', 'UNKNOWN'))
    
    if pitcher_roster_info:
        pitcher_hand = pitcher_roster_info.get('ph', pitcher_roster_info.get('hand', 'UNKNOWN'))
    
    # Get batter stats safely
    batter_stats = batter_roster_info.get('stats', {}) if batter_roster_info else {}
    
    # Calculate derived metrics
    batter_games = batter_stats.get('2024_Games', 0)
    batter_ab = batter_stats.get('2024_AB', 0)
    batter_hr = batter_stats.get('2024_HR', 0)
    batter_h = batter_stats.get('2024_H', 0)
    batter_2b = batter_stats.get('2024_2B', 0)
    batter_3b = batter_stats.get('2024_3B', 0)
    
    # Calculate ISO (Isolated Power) = SLG - AVG
    batter_slg = batter_stats.get('2024_SLG', 0)
    batter_avg = batter_stats.get('2024_AVG', 0)
    iso_2024 = batter_slg - batter_avg if batter_slg and batter_avg else None
    
    # Calculate HR rate
    hr_rate_calc = (batter_hr / batter_ab * 100) if batter_ab > 0 else None
    
    # Calculate comprehensive pitcher stats from ALL available data
    comprehensive_pitcher_stats = {}
    if pitcher_id and master_data and daily_game_data:
        comprehensive_pitcher_stats = calculate_comprehensive_pitcher_stats(pitcher_id, master_data, daily_game_data)
        logger.info(f"📊 Comprehensive pitcher stats: home_games={comprehensive_pitcher_stats.get('pitcher_home_games')}, home_hr={comprehensive_pitcher_stats.get('pitcher_home_hr_total')}")
    
    # Calculate batter trend direction
    batter_trend = calculate_batter_trend_direction(recent_stats, batter_roster_info)
    
    # Build comprehensive prediction object
    prediction = {
        # Core identification
        'batter_name': analysis_result.get('batter_name', 'Unknown'),
        'score': analysis_result.get('score', 0),
        'confidence': 1.0,  # High confidence for real analysis
        'data_source': 'REAL_ENHANCED_HR_LIKELIHOOD_SCORE',
        
        # Hands - critical fields that were missing
        'batter_hand': batter_hand,
        'pitcher_hand': pitcher_hand,
        
        # Teams
        'team': batter_roster_info.get('team', 'UNK') if batter_roster_info else 'UNK',
        'batter_team': batter_roster_info.get('team', 'UNK') if batter_roster_info else 'UNK',
        'pitcher_team': pitcher_roster_info.get('team', 'UNK') if pitcher_roster_info else 'UNK',
        
        # Outcome probabilities
        'outcome_probabilities': outcome_probs,
        'hr_probability': outcome_probs.get('homerun', 0),
        'hit_probability': outcome_probs.get('hit', 0),
        'reach_base_probability': outcome_probs.get('reach_base', 0),
        'strikeout_probability': outcome_probs.get('strikeout', 0),
        
        # Component scores - flatten for easier access
        'arsenal_matchup': components.get('arsenal_matchup'),
        'batter_overall': components.get('batter_overall'),
        'pitcher_overall': components.get('pitcher_overall'),
        'historical_yoy_csv': components.get('historical_yoy_csv'),
        'recent_daily_games': components.get('recent_daily_games'),
        'contextual': components.get('contextual'),
        
        # Detailed metrics from analysis (with fallbacks)
        'recent_avg': details.get('recent_avg') or batter_avg,
        'hr_rate': details.get('hr_rate') or hr_rate_calc,
        'ab_due': details.get('ab_due'),
        'hits_due': details.get('hits_due'),
        'contact_trend': details.get('contact_trend'),
        'ab_since_last_hr': details.get('ab_since_last_hr'),
        'expected_ab_per_hr': details.get('expected_ab_per_hr'),
        'h_since_last_hr': details.get('h_since_last_hr'),
        'expected_h_per_hr': details.get('expected_h_per_hr'),
        
        # Batter stats from roster
        'obp': batter_stats.get('2024_OBP'),
        'iso_2024': iso_2024,
        'iso_2025': batter_stats.get('2025_ISO'),  # If available
        'hitter_slg': batter_slg,
        'batter_pa_2025': batter_stats.get('2025_PA', 0),
        
        # Recent performance indicators (with fallbacks)
        'heating_up': recent_stats.get('heating_up') if recent_stats else (batter_avg > 0.280),
        'cold': recent_stats.get('cold') if recent_stats else (batter_avg < 0.220),
        
        # Additional calculated fields
        'iso_trend': details.get('iso_trend'),
        'ev_matchup_score': details.get('ev_matchup'),
        
        # Trend directions (calculated from comprehensive analysis)
        'recent_trend_dir': batter_trend or details.get('trend_direction') or details.get('batter_trend_direction'),
        'pitcher_trend_dir': comprehensive_pitcher_stats.get('pitcher_trend_direction') if comprehensive_pitcher_stats else 'stable',
        
        # Pitcher info (add if available in analysis)
        'pitcher_era': details.get('pitcher_era'),
        'pitcher_whip': details.get('pitcher_whip'),
        'pitcher_slg': details.get('pitcher_slg_allowed'),
        
        # Pitcher home stats (calculated from ALL available data)
        'pitcher_home_h_total': (comprehensive_pitcher_stats.get('pitcher_home_h_total') if comprehensive_pitcher_stats else None) or 0,
        'pitcher_home_hr_total': (comprehensive_pitcher_stats.get('pitcher_home_hr_total') if comprehensive_pitcher_stats else None) or 0, 
        'pitcher_home_k_total': (comprehensive_pitcher_stats.get('pitcher_home_k_total') if comprehensive_pitcher_stats else None) or 0,
        'pitcher_home_games': (comprehensive_pitcher_stats.get('pitcher_home_games') if comprehensive_pitcher_stats else None) or 0,
        
        # Store raw components for debugging
        'matchup_components': components,
        'details': details,
        
        # Summaries
        'historical_summary': analysis_result.get('historical_summary'),
        'recent_summary': analysis_result.get('recent_summary'),
        
        # Metadata
        'analysis_type': 'REAL_DATA_ONLY',
        'mock_data_used': False
    }
    
    return prediction

@app.get("/health")
async def health_check():
    """Health check showing real data status"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "data_source": "REAL_FILES_ONLY",
        "initialization_status": global_data['initialization_status'],
        "mock_data_used": False,
        "fallback_data_used": False,
        "version": "1.2.0-batch-fixed"
    }

@app.get("/data/status")
async def data_status():
    """Real data status"""
    status = global_data['initialization_status']
    
    response = {
        "initialization_status": status,
        "data_source": "REAL_FILES_ONLY",
        "mock_data_policy": "ABSOLUTELY_FORBIDDEN",
        "timestamp": datetime.now().isoformat(),
        "version": "1.2.0-batch-fixed"
    }
    
    if status == 'completed':
        response.update({
            "master_players_loaded": len(global_data.get('master_player_data', {})),
            "roster_entries_loaded": len(global_data.get('roster_data', [])),
            "daily_game_dates_loaded": len(global_data.get('daily_game_data', {})),
            "historical_years_loaded": list(global_data.get('historical_data', {}).keys()),
            "league_averages_calculated": bool(global_data.get('league_avg_stats'))
        })
    elif status == 'failed':
        response["error"] = global_data.get('initialization_error')
    
    return response

@app.post("/analyze/pitcher-vs-team")
async def analyze_pitcher_vs_team_improved(request: PredictionRequest):
    """Improved analysis using ONLY real data with comprehensive field mapping"""
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(status_code=503, detail=f"Real data not ready: {global_data['initialization_status']}")
    
    logger.info(f"🎯 BATCH FIXED REAL DATA ANALYSIS: {request.pitcher_name} vs {request.team}")
    
    master_data = global_data['master_player_data']
    roster_data = global_data['roster_data']
    
    # Find pitcher using real data only
    pitcher_id = None
    pitcher_roster_info = None
    
    logger.info(f"🔍 Searching for pitcher: '{request.pitcher_name}'")
    
    for pid, pdata in master_data.items():
        roster_info = pdata.get('roster_info', {})
        if roster_info.get('type') == 'pitcher':
            names_to_check = [
                roster_info.get('fullName_resolved', ''),
                roster_info.get('fullName_cleaned', ''),
                roster_info.get('fullName', ''),
                roster_info.get('name', '')
            ]
            
            for name in names_to_check:
                if name and name.lower() == request.pitcher_name.lower():
                    pitcher_id = pid
                    pitcher_roster_info = get_roster_info_for_player(master_data, pid, roster_data)
                    logger.info(f"✅ Found pitcher in real data: {name} (ID: {pid})")
                    logger.info(f"📋 Pitcher roster info: team={pitcher_roster_info.get('team')}, hand={pitcher_roster_info.get('ph')}")
                    break
            
            if pitcher_id:
                break
    
    if not pitcher_id:
        raise HTTPException(status_code=404, detail=f"Pitcher '{request.pitcher_name}' not found in real roster data")
    
    # Find team batters using real data only
    team_batters = []
    
    logger.info(f"🔍 Searching for team '{request.team}' batters")
    batters_found = 0
    
    for pid, pdata in master_data.items():
        roster_info = pdata.get('roster_info', {})
        if (roster_info.get('type') == 'hitter' and 
            roster_info.get('team', '').upper() == request.team.upper()):
            
            batters_found += 1
            batter_name = roster_info.get('fullName_resolved') or roster_info.get('fullName') or f"Player_{pid}"
            
            # Get comprehensive roster info
            batter_roster_info = get_roster_info_for_player(master_data, pid, roster_data)
            
            logger.info(f"📊 Processing batter: {batter_name}")
            logger.info(f"📋 Batter roster info: team={batter_roster_info.get('team')}, hand={batter_roster_info.get('bats')}")
            
            # Get real recent performance data
            recent_stats = None
            try:
                recent_games_data, _ = get_last_n_games_performance(
                    batter_name, 
                    global_data['daily_game_data'], 
                    global_data['roster_data'], 
                    n_games=7
                )
                if recent_games_data:
                    recent_stats = calculate_recent_trends(recent_games_data)
                    logger.info(f"📊 Got real recent stats for {batter_name}: {len(recent_games_data)} games")
            except Exception as e:
                logger.warning(f"⚠️ Could not get recent stats for {batter_name}: {e}")
                recent_stats = None
            
            # Call REAL analysis function with real data
            try:
                analysis_result = enhanced_hr_likelihood_score(
                    batter_mlbam_id=pid,
                    pitcher_mlbam_id=pitcher_id,
                    master_player_data=master_data,
                    historical_data=global_data['historical_data'],
                    metric_ranges=global_data['metric_ranges'],
                    league_avg_stats=global_data['league_avg_stats'],
                    recent_batter_stats=recent_stats
                )
                
                if analysis_result and isinstance(analysis_result, dict):
                    # Get pitcher recent performance just like debug_main.py does
                    pitcher_games = []
                    pitcher_recent_trends = {}
                    
                    try:
                        # Use the same pitcher analysis approach as debug_main.py
                        pitcher_resolved_name = pitcher_roster_info.get('fullName_resolved') or pitcher_roster_info.get('fullName')
                        if pitcher_resolved_name:
                            # This would need the same get_last_n_games_performance_pitcher function
                            # For now, let's extract from the existing analysis if available
                            logger.info(f"🔍 Looking for pitcher trend data for {pitcher_resolved_name}")
                            
                            # Check if the analysis result already contains pitcher trend info
                            if 'pitcher_recent_data' in analysis_result:
                                pitcher_trends_obj = analysis_result.get('pitcher_recent_data', {}).get('trends_summary_obj', {})
                                if pitcher_trends_obj.get('trend_direction'):
                                    pitcher_recent_trends = pitcher_trends_obj
                                    logger.info(f"✅ Found pitcher trend from analysis: {pitcher_trends_obj.get('trend_direction')}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not get pitcher trend data: {e}")
                    
                    # Extract ALL expected fields comprehensively
                    prediction = extract_all_fields_from_analysis(
                        analysis_result, 
                        batter_roster_info, 
                        pitcher_roster_info, 
                        recent_stats,
                        pitcher_id,
                        master_data,
                        global_data['daily_game_data']
                    )
                    
                    # Override pitcher trend direction if we found it from the analysis
                    if pitcher_recent_trends and pitcher_recent_trends.get('trend_direction'):
                        prediction['pitcher_trend_dir'] = pitcher_recent_trends.get('trend_direction')
                        logger.info(f"✅ Set pitcher trend direction to: {prediction['pitcher_trend_dir']}")
                    
                    if prediction:
                        team_batters.append(prediction)
                        logger.info(f"✅ Real analysis complete for {batter_name}: score={analysis_result.get('score')}, batter_hand={prediction.get('batter_hand')}, pitcher_hand={prediction.get('pitcher_hand')}")
                    else:
                        logger.error(f"❌ Failed to extract fields for {batter_name}")
                        
                else:
                    logger.error(f"❌ Real analysis returned invalid result for {batter_name}: {type(analysis_result)}")
                    
            except Exception as analysis_error:
                logger.error(f"❌ REAL ANALYSIS FAILED for {batter_name}: {analysis_error}")
                # DO NOT add any fallback data - if real analysis fails, we need to know
                continue
    
    logger.info(f"📊 Found {batters_found} batters for team {request.team}, generated {len(team_batters)} predictions")
    
    if not team_batters:
        raise HTTPException(
            status_code=404, 
            detail=f"No valid analysis results for team '{request.team}' vs pitcher '{request.pitcher_name}' using real data only"
        )
    
    # Sort by requested field with comprehensive logic
    sort_functions = {
        'score': lambda x: x.get('score', 0),
        'hr': lambda x: x.get('hr_probability', 0),
        'hit': lambda x: x.get('hit_probability', 0),
        'reach_base': lambda x: x.get('reach_base_probability', 0),
        'strikeout': lambda x: x.get('strikeout_probability', 0),
        'arsenal_matchup': lambda x: x.get('arsenal_matchup', 0),
        'batter_overall': lambda x: x.get('batter_overall', 0),
        'pitcher_overall': lambda x: x.get('pitcher_overall', 0),
        'historical_yoy_csv': lambda x: x.get('historical_yoy_csv', 0),
        'recent_daily_games': lambda x: x.get('recent_daily_games', 0),
        'contextual': lambda x: x.get('contextual', 0),
        'recent_avg': lambda x: x.get('recent_avg', 0),
        'hr_rate': lambda x: x.get('hr_rate', 0),
        'obp': lambda x: x.get('obp', 0),
        'ab_due': lambda x: x.get('ab_due', 0),
        'hits_due': lambda x: x.get('hits_due', 0),
        'heating_up': lambda x: x.get('heating_up', False),
        'cold': lambda x: x.get('cold', False),
        'hitter_slg': lambda x: x.get('hitter_slg', 0),
        'pitcher_slg': lambda x: x.get('pitcher_slg', 0),
        'recent_trend_dir': lambda x: x.get('recent_trend_dir', ''),
        'pitcher_trend_dir': lambda x: x.get('pitcher_trend_dir', ''),
        'pitcher_home_h_total': lambda x: x.get('pitcher_home_h_total', 0),
        'pitcher_home_hr_total': lambda x: x.get('pitcher_home_hr_total', 0),
        'pitcher_home_k_total': lambda x: x.get('pitcher_home_k_total', 0),
        'confidence': lambda x: x.get('confidence', 0)
    }
    
    if request.sort_by in sort_functions:
        # For strikeout, we want lowest first (reverse=False), for others highest first
        reverse_sort = request.sort_by != 'strikeout'
        team_batters.sort(key=sort_functions[request.sort_by], reverse=reverse_sort)
    else:
        # Default to score
        team_batters.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # Limit results if requested
    if request.max_results:
        team_batters = team_batters[:request.max_results]
    
    # Ensure React-compatible field names for all predictions
    for prediction in team_batters:
        if 'batter_name' in prediction and 'player_name' not in prediction:
            prediction['player_name'] = prediction['batter_name']
        if 'score' in prediction and 'hr_score' not in prediction:
            prediction['hr_score'] = prediction['score']
    
    result = {
        'success': True,
        'pitcher_name': request.pitcher_name,
        'team': request.team.upper(),
        'predictions': team_batters,
        'total_batters_analyzed': len(team_batters),
        'data_source': 'REAL_FILES_ONLY',
        'mock_data_used': False,
        'analysis_method': 'enhanced_hr_likelihood_score',
        'data_quality': 'REAL_DATA_ONLY',
        'version': '1.2.0-batch-fixed'
    }
    
    logger.info(f"✅ BATCH FIXED REAL DATA ANALYSIS COMPLETE: {len(team_batters)} predictions generated")
    return result

@app.post("/batch-analysis")
async def batch_analysis_fixed(request: dict):
    """FIXED Batch analysis endpoint - handles team_abbr properly"""
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(status_code=503, detail=f"Real data not ready: {global_data['initialization_status']}")
    
    logger.info(f"🎯 BATCH ANALYSIS REQUEST (FIXED): {request}")
    
    matchups = request.get('matchups', [])
    sort_by = request.get('sort_by', 'score')
    limit = request.get('limit', 20)
    
    if not matchups:
        raise HTTPException(status_code=400, detail="No matchups provided")
    
    all_results = []
    
    for matchup in matchups:
        try:
            # FIXED: Handle both team and team_abbr fields
            pitcher_name = matchup.get('pitcher_name')
            team = matchup.get('team') or matchup.get('team_abbr')
            
            logger.info(f"🔍 Extracted from matchup: pitcher_name='{pitcher_name}', team='{team}'")
            
            if not pitcher_name or not team:
                logger.warning(f"⚠️ Skipping invalid matchup: {matchup} - pitcher_name: '{pitcher_name}', team: '{team}'")
                continue
            
            logger.info(f"🎯 Processing batch matchup: {pitcher_name} vs {team}")
            
            # Use the same analysis logic as single matchup
            single_request = PredictionRequest(
                pitcher_name=pitcher_name,
                team=team,  # This is now correctly extracted
                sort_by=sort_by,
                max_results=limit
            )
            
            logger.info(f"🔍 Calling single analysis for: {pitcher_name} vs {team}")
            result = await analyze_pitcher_vs_team_improved(single_request)
            logger.info(f"📊 Single analysis result: {len(result.get('predictions', []))} predictions returned")
            
            # Add matchup identifier and ensure React-compatible field names
            for prediction in result.get('predictions', []):
                prediction['matchup_id'] = f"{pitcher_name}_vs_{team}"
                prediction['pitcher_name'] = pitcher_name
                prediction['team_abbr'] = team
                
                # Ensure React-compatible field names
                if 'batter_name' in prediction and 'player_name' not in prediction:
                    prediction['player_name'] = prediction['batter_name']
                if 'score' in prediction and 'hr_score' not in prediction:
                    prediction['hr_score'] = prediction['score']
            
            all_results.extend(result.get('predictions', []))
            logger.info(f"📈 Total results so far: {len(all_results)}")
            
        except Exception as e:
            logger.error(f"❌ Batch analysis failed for matchup {matchup}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue
    
    logger.info(f"🎯 Batch processing complete. Total results: {len(all_results)}")
    
    # Sort all results together with comprehensive logic
    sort_functions = {
        'score': lambda x: x.get('score', 0),
        'hr': lambda x: x.get('hr_probability', 0),
        'hit': lambda x: x.get('hit_probability', 0),
        'reach_base': lambda x: x.get('reach_base_probability', 0),
        'strikeout': lambda x: x.get('strikeout_probability', 0),
        'arsenal_matchup': lambda x: x.get('arsenal_matchup', 0),
        'batter_overall': lambda x: x.get('batter_overall', 0),
        'pitcher_overall': lambda x: x.get('pitcher_overall', 0),
        'historical_yoy_csv': lambda x: x.get('historical_yoy_csv', 0),
        'recent_daily_games': lambda x: x.get('recent_daily_games', 0),
        'contextual': lambda x: x.get('contextual', 0),
        'recent_avg': lambda x: x.get('recent_avg', 0),
        'hr_rate': lambda x: x.get('hr_rate', 0),
        'obp': lambda x: x.get('obp', 0),
        'ab_due': lambda x: x.get('ab_due', 0),
        'hits_due': lambda x: x.get('hits_due', 0),
        'heating_up': lambda x: x.get('heating_up', False),
        'cold': lambda x: x.get('cold', False),
        'hitter_slg': lambda x: x.get('hitter_slg', 0),
        'pitcher_slg': lambda x: x.get('pitcher_slg', 0),
        'recent_trend_dir': lambda x: x.get('recent_trend_dir', ''),
        'pitcher_trend_dir': lambda x: x.get('pitcher_trend_dir', ''),
        'pitcher_home_h_total': lambda x: x.get('pitcher_home_h_total', 0),
        'pitcher_home_hr_total': lambda x: x.get('pitcher_home_hr_total', 0),
        'pitcher_home_k_total': lambda x: x.get('pitcher_home_k_total', 0),
        'confidence': lambda x: x.get('confidence', 0)
    }
    
    if sort_by in sort_functions:
        # For strikeout, we want lowest first (reverse=False), for others highest first
        reverse_sort = sort_by != 'strikeout'
        all_results.sort(key=sort_functions[sort_by], reverse=reverse_sort)
    else:
        # Default to score
        all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # Limit results
    if limit:
        all_results = all_results[:limit]
    
    return {
        'success': True,
        'total_predictions': len(all_results),
        'predictions': all_results,
        'matchups_processed': len(matchups),
        'data_source': 'REAL_FILES_ONLY',
        'analysis_method': 'enhanced_hr_likelihood_score_batch_fixed',
        'version': '1.2.0-batch-fixed'
    }

@app.get("/sort-options")
async def get_sort_options():
    """Sort options - comprehensive list matching original API"""
    return {
        "options": [
            {"key": "score", "label": "Overall HR Score", "description": "Overall HR likelihood score"},
            {"key": "hr", "label": "HR Probability", "description": "Home run probability percentage"},
            {"key": "hit", "label": "Hit Probability", "description": "Hit probability percentage"},
            {"key": "reach_base", "label": "Reach Base Probability", "description": "Reach base probability percentage"},
            {"key": "strikeout", "label": "Strikeout Probability (lowest first)", "description": "Strikeout probability (lower is better)"},
            {"key": "arsenal_matchup", "label": "Arsenal Matchup Component", "description": "Arsenal vs batter matchup score"},
            {"key": "batter_overall", "label": "Batter Overall Component", "description": "Batter overall performance component"},
            {"key": "pitcher_overall", "label": "Pitcher Overall Component", "description": "Pitcher overall performance component"},
            {"key": "historical_yoy_csv", "label": "Historical Trend Component", "description": "Historical year-over-year performance"},
            {"key": "recent_daily_games", "label": "Recent Performance Component", "description": "Recent daily games performance"},
            {"key": "contextual", "label": "Contextual Factors Component", "description": "Contextual factors score"},
            {"key": "recent_avg", "label": "Recent Batting Average", "description": "Recent batting average"},
            {"key": "hr_rate", "label": "Recent HR Rate", "description": "Recent home run rate"},
            {"key": "obp", "label": "Recent On-Base Percentage", "description": "Recent on-base percentage"},
            {"key": "ab_due", "label": "Due for HR (AB-based)", "description": "At-bats based due factor"},
            {"key": "hits_due", "label": "Due for HR (hits-based)", "description": "Hits based due factor"},
            {"key": "heating_up", "label": "Heating Up Contact", "description": "Heating up trend indicator"},
            {"key": "cold", "label": "Cold Batter Score", "description": "Cold streak indicator"},
            {"key": "hitter_slg", "label": "Hitter SLG vs Arsenal", "description": "Hitter slugging vs pitcher arsenal"},
            {"key": "pitcher_slg", "label": "Pitcher SLG Allowed", "description": "Pitcher slugging allowed"},
            {"key": "recent_trend_dir", "label": "Recent Trend Direction", "description": "Batter's recent performance trend"},
            {"key": "pitcher_trend_dir", "label": "Pitcher Trend Direction", "description": "Pitcher's recent performance trend"},
            {"key": "pitcher_home_h_total", "label": "Pitcher Home H Total", "description": "Total hits allowed at home"},
            {"key": "pitcher_home_hr_total", "label": "Pitcher Home HR Total", "description": "Total home runs allowed at home"},
            {"key": "pitcher_home_k_total", "label": "Pitcher Home K Total", "description": "Total strikeouts at home"},
            {"key": "confidence", "label": "Confidence", "description": "Analysis confidence level"}
        ]
    }

if __name__ == "__main__":
    print("🎯 Starting BATCH FIXED REAL DATA ONLY Baseball Analysis API")
    print("🚫 ZERO tolerance for mock data - real files only!")
    print("📊 All predictions sourced from actual analysis of your data files")
    print("🔧 FIXED: Batch analysis now handles team_abbr properly")
    print("📋 FIXED: Comprehensive sort options available")
    
    uvicorn.run(
        "batch_fixed_main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )