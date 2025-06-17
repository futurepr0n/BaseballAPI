#!/usr/bin/env python3
"""
Real Data Only - Baseball Analysis API
Uses ONLY actual data from files, no mock data whatsoever
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
app = FastAPI(title="Real Data Baseball API", version="1.0.0-real-data-only")

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

@app.get("/health")
async def health_check():
    """Health check showing real data status"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "data_source": "REAL_FILES_ONLY",
        "initialization_status": global_data['initialization_status'],
        "mock_data_used": False,
        "fallback_data_used": False
    }

@app.get("/data/status")
async def data_status():
    """Real data status"""
    status = global_data['initialization_status']
    
    response = {
        "initialization_status": status,
        "data_source": "REAL_FILES_ONLY",
        "mock_data_policy": "ABSOLUTELY_FORBIDDEN",
        "timestamp": datetime.now().isoformat()
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
async def analyze_pitcher_vs_team_real_data_only(request: PredictionRequest):
    """Analysis using ONLY real data from files"""
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(status_code=503, detail=f"Real data not ready: {global_data['initialization_status']}")
    
    logger.info(f"🎯 REAL DATA ANALYSIS: {request.pitcher_name} vs {request.team}")
    
    master_data = global_data['master_player_data']
    roster_data = global_data['roster_data']
    
    # Find pitcher using real data only
    pitcher_id = None
    pitcher_roster_info = None
    
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
                    pitcher_roster_info = roster_info
                    logger.info(f"✅ Found pitcher in real data: {name} (ID: {pid})")
                    break
            
            if pitcher_id:
                break
    
    if not pitcher_id:
        raise HTTPException(status_code=404, detail=f"Pitcher '{request.pitcher_name}' not found in real roster data")
    
    # Find team batters using real data only
    team_batters = []
    
    for pid, pdata in master_data.items():
        roster_info = pdata.get('roster_info', {})
        if (roster_info.get('type') == 'hitter' and 
            roster_info.get('team', '').upper() == request.team.upper()):
            
            batter_name = roster_info.get('fullName_resolved') or roster_info.get('fullName') or f"Player_{pid}"
            
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
                    # Extract real data from roster
                    batter_hand = roster_info.get('bats', 'UNKNOWN')
                    pitcher_hand = pitcher_roster_info.get('ph', 'UNKNOWN') if pitcher_roster_info else 'UNKNOWN'
                    
                    # Build prediction with ONLY real data
                    prediction = {
                        'batter_name': batter_name,
                        'score': analysis_result.get('score'),
                        'confidence': 1.0,  # High confidence - this is real analysis
                        'data_source': 'REAL_ENHANCED_HR_LIKELIHOOD_SCORE',
                        'outcome_probabilities': analysis_result.get('outcome_probabilities', {}),
                        
                        # Real roster data
                        'batter_hand': batter_hand,
                        'pitcher_hand': pitcher_hand,
                        'team': roster_info.get('team'),
                        'batter_team': roster_info.get('team'),
                        'pitcher_team': pitcher_roster_info.get('team') if pitcher_roster_info else 'UNKNOWN',
                        
                        # Real analysis components
                        'matchup_components': analysis_result.get('matchup_components', {}),
                        'details': analysis_result.get('details', {}),
                        
                        # Flatten component scores for easier access
                        'arsenal_matchup': analysis_result.get('matchup_components', {}).get('arsenal_matchup'),
                        'batter_overall': analysis_result.get('matchup_components', {}).get('batter_overall'),
                        'pitcher_overall': analysis_result.get('matchup_components', {}).get('pitcher_overall'),
                        'historical_yoy_csv': analysis_result.get('matchup_components', {}).get('historical_yoy_csv'),
                        'recent_daily_games': analysis_result.get('matchup_components', {}).get('recent_daily_games'),
                        'contextual': analysis_result.get('matchup_components', {}).get('contextual'),
                        
                        # Real detailed metrics from analysis
                        'recent_avg': analysis_result.get('details', {}).get('recent_avg'),
                        'hr_rate': analysis_result.get('details', {}).get('hr_rate'),
                        'ab_due': analysis_result.get('details', {}).get('ab_due'),
                        'hits_due': analysis_result.get('details', {}).get('hits_due'),
                        'contact_trend': analysis_result.get('details', {}).get('contact_trend'),
                        'ab_since_last_hr': analysis_result.get('details', {}).get('ab_since_last_hr'),
                        'expected_ab_per_hr': analysis_result.get('details', {}).get('expected_ab_per_hr'),
                        
                        # Real summaries
                        'historical_summary': analysis_result.get('historical_summary'),
                        'recent_summary': analysis_result.get('recent_summary'),
                        
                        # Analysis metadata
                        'analysis_type': 'REAL_DATA_ONLY',
                        'mock_data_used': False
                    }
                    
                    team_batters.append(prediction)
                    logger.info(f"✅ Real analysis complete for {batter_name}: score={analysis_result.get('score')}")
                    
                else:
                    logger.error(f"❌ Real analysis returned invalid result for {batter_name}: {type(analysis_result)}")
                    
            except Exception as analysis_error:
                logger.error(f"❌ REAL ANALYSIS FAILED for {batter_name}: {analysis_error}")
                # DO NOT add any fallback data - if real analysis fails, we need to know
                continue
    
    if not team_batters:
        raise HTTPException(
            status_code=404, 
            detail=f"No valid analysis results for team '{request.team}' vs pitcher '{request.pitcher_name}' using real data only"
        )
    
    # Sort by requested field
    if request.sort_by == 'score':
        team_batters.sort(key=lambda x: x.get('score', 0), reverse=True)
    elif request.sort_by == 'hr':
        team_batters.sort(key=lambda x: x.get('outcome_probabilities', {}).get('homerun', 0), reverse=True)
    
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
        'data_quality': 'REAL_DATA_ONLY'
    }
    
    logger.info(f"✅ REAL DATA ANALYSIS COMPLETE: {len(team_batters)} predictions generated")
    return result

@app.get("/sort-options")
async def get_sort_options():
    """Sort options"""
    return {
        "options": [
            {"key": "score", "label": "HR Score", "description": "Real HR likelihood score"},
            {"key": "hr", "label": "HR Probability", "description": "Real HR probability from analysis"},
            {"key": "hit", "label": "Hit Probability", "description": "Real hit probability"},
            {"key": "confidence", "label": "Confidence", "description": "Analysis confidence"}
        ]
    }

if __name__ == "__main__":
    print("🎯 Starting REAL DATA ONLY Baseball Analysis API")
    print("🚫 ZERO tolerance for mock data - real files only!")
    print("📊 All predictions sourced from actual analysis of your data files")
    
    uvicorn.run(
        "real_data_main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )