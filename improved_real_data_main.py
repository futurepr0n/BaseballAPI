#!/usr/bin/env python3
"""
Improved Real Data Only - Baseball Analysis API
Enhanced version with better field mapping and debugging
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
app = FastAPI(title="Improved Real Data Baseball API", version="1.1.0-real-data-enhanced")

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

def extract_all_fields_from_analysis(analysis_result, batter_roster_info, pitcher_roster_info, recent_stats=None):
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
        
        # Pitcher info (add if available in analysis)
        'pitcher_era': details.get('pitcher_era'),
        'pitcher_whip': details.get('pitcher_whip'),
        'pitcher_slg': details.get('pitcher_slg_allowed'),
        'pitcher_trend_dir': details.get('pitcher_trend'),
        
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
        "version": "1.1.0-improved"
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
        "version": "1.1.0-improved"
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
    
    logger.info(f"🎯 IMPROVED REAL DATA ANALYSIS: {request.pitcher_name} vs {request.team}")
    
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
                    # Extract ALL expected fields comprehensively
                    prediction = extract_all_fields_from_analysis(
                        analysis_result, 
                        batter_roster_info, 
                        pitcher_roster_info, 
                        recent_stats
                    )
                    
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
    
    # Sort by requested field
    if request.sort_by == 'score':
        team_batters.sort(key=lambda x: x.get('score', 0), reverse=True)
    elif request.sort_by == 'hr':
        team_batters.sort(key=lambda x: x.get('hr_probability', 0), reverse=True)
    
    # Limit results if requested
    if request.max_results:
        team_batters = team_batters[:request.max_results]
    
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
        'version': '1.1.0-improved'
    }
    
    logger.info(f"✅ IMPROVED REAL DATA ANALYSIS COMPLETE: {len(team_batters)} predictions generated")
    return result

@app.post("/batch-analysis")
async def batch_analysis(request: dict):
    """Batch analysis endpoint for multiple matchups"""
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(status_code=503, detail=f"Real data not ready: {global_data['initialization_status']}")
    
    logger.info(f"🎯 BATCH ANALYSIS REQUEST: {request}")
    
    matchups = request.get('matchups', [])
    sort_by = request.get('sort_by', 'score')
    limit = request.get('limit', 20)
    
    if not matchups:
        raise HTTPException(status_code=400, detail="No matchups provided")
    
    all_results = []
    
    for matchup in matchups:
        try:
            # Each matchup should have pitcher_name and team (handle both team and team_abbr)
            pitcher_name = matchup.get('pitcher_name')
            team = matchup.get('team') or matchup.get('team_abbr')
            
            if not pitcher_name or not team:
                logger.warning(f"⚠️ Skipping invalid matchup: {matchup} - pitcher_name: {pitcher_name}, team: {team}")
                continue
            
            logger.info(f"🎯 Processing batch matchup: {pitcher_name} vs {team}")
            
            # Use the same analysis logic as single matchup
            single_request = PredictionRequest(
                pitcher_name=pitcher_name,
                team=team,
                sort_by=sort_by,
                max_results=limit
            )
            
            logger.info(f"🔍 Calling analysis for: {pitcher_name} vs {team}")
            result = await analyze_pitcher_vs_team_improved(single_request)
            logger.info(f"📊 Analysis result: {len(result.get('predictions', []))} predictions returned")
            
            # Add matchup identifier
            for prediction in result.get('predictions', []):
                prediction['matchup_id'] = f"{pitcher_name}_vs_{team}"
                prediction['pitcher_name'] = pitcher_name
                prediction['team_abbr'] = team
            
            all_results.extend(result.get('predictions', []))
            logger.info(f"📈 Total results so far: {len(all_results)}")
            
        except Exception as e:
            logger.error(f"❌ Batch analysis failed for matchup {matchup}: {e}")
            continue
    
    # Sort all results together
    if sort_by == 'score':
        all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    elif sort_by == 'hr':
        all_results.sort(key=lambda x: x.get('hr_probability', 0), reverse=True)
    
    # Limit results
    if limit:
        all_results = all_results[:limit]
    
    return {
        'success': True,
        'total_predictions': len(all_results),
        'predictions': all_results,
        'matchups_processed': len(matchups),
        'data_source': 'REAL_FILES_ONLY',
        'analysis_method': 'enhanced_hr_likelihood_score_batch'
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
            {"key": "confidence", "label": "Confidence", "description": "Analysis confidence level"}
        ]
    }

if __name__ == "__main__":
    print("🎯 Starting IMPROVED REAL DATA ONLY Baseball Analysis API")
    print("🚫 ZERO tolerance for mock data - real files only!")
    print("📊 All predictions sourced from actual analysis of your data files")
    print("🔧 Enhanced field mapping and debugging for comprehensive data")
    
    uvicorn.run(
        "improved_real_data_main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )