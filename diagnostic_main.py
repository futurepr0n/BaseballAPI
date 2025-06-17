#!/usr/bin/env python3
"""
Diagnostic version to debug the analysis issues
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import logging
from datetime import datetime

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Try to import required modules with detailed error reporting
try:
    from utils import find_player_id_by_name, clean_player_name
    logger.info("✅ Utils imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import utils: {e}")

try:
    from data_loader import initialize_data, get_last_n_games_performance
    logger.info("✅ Data loader imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import data_loader: {e}")

try:
    from analyzer import enhanced_hr_likelihood_score, calculate_recent_trends
    logger.info("✅ Original analyzer imported successfully")
    original_analyzer_available = True
except ImportError as e:
    logger.error(f"❌ Failed to import original analyzer: {e}")
    original_analyzer_available = False

# Create FastAPI app
app = FastAPI(title="Diagnostic Baseball API", version="1.0.0-debug")

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
    'initialization_status': 'not_started',
    'initialization_error': None,
    'debug_info': {}
}

@app.on_event("startup")
async def startup_event():
    """Initialize with detailed debugging"""
    await initialize_with_debugging()

async def initialize_with_debugging():
    """Initialize data with detailed debugging information"""
    try:
        global_data['initialization_status'] = 'in_progress'
        logger.info("🔍 Starting detailed data initialization...")
        
        # Initialize base data
        logger.info("📊 Calling initialize_data()...")
        result = initialize_data()
        
        if not result:
            raise ValueError("initialize_data() returned None")
        
        if len(result) != 8:
            raise ValueError(f"initialize_data() returned {len(result)} items, expected 8")
        
        (master_player_data, player_id_to_name_map, name_to_player_id_map, 
         daily_game_data, roster_data, historical_data, league_avg_stats, metric_ranges) = result
        
        # Store and analyze the data
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
        
        # Debug information
        debug_info = {
            'total_players': len(master_player_data) if master_player_data else 0,
            'pitcher_count': 0,
            'hitter_count': 0,
            'teams_found': set(),
            'sample_pitchers': [],
            'sample_hitters': [],
            'daily_game_dates': len(daily_game_data) if daily_game_data else 0,
            'roster_count': len(roster_data) if roster_data else 0
        }
        
        # Analyze the loaded data
        if master_player_data:
            for pid, pdata in master_player_data.items():
                roster_info = pdata.get('roster_info', {})
                player_type = roster_info.get('type')
                team = roster_info.get('team')
                name = roster_info.get('fullName_resolved', roster_info.get('name', 'Unknown'))
                
                if player_type == 'pitcher':
                    debug_info['pitcher_count'] += 1
                    if len(debug_info['sample_pitchers']) < 5:
                        debug_info['sample_pitchers'].append({
                            'id': pid,
                            'name': name,
                            'team': team
                        })
                elif player_type == 'hitter':
                    debug_info['hitter_count'] += 1
                    if len(debug_info['sample_hitters']) < 5:
                        debug_info['sample_hitters'].append({
                            'id': pid,
                            'name': name,
                            'team': team
                        })
                
                if team:
                    debug_info['teams_found'].add(team)
        
        debug_info['teams_found'] = list(debug_info['teams_found'])
        global_data['debug_info'] = debug_info
        global_data['initialization_status'] = 'completed'
        
        logger.info("🎉 Data initialization completed!")
        logger.info(f"📊 Total players: {debug_info['total_players']}")
        logger.info(f"⚾ Pitchers: {debug_info['pitcher_count']}")
        logger.info(f"🏏 Hitters: {debug_info['hitter_count']}")
        logger.info(f"🏟️ Teams: {len(debug_info['teams_found'])}")
        logger.info(f"📅 Daily game dates: {debug_info['daily_game_dates']}")
        
        if debug_info['sample_pitchers']:
            logger.info(f"🎯 Sample pitchers: {[p['name'] for p in debug_info['sample_pitchers']]}")
        
    except Exception as e:
        global_data['initialization_status'] = 'failed'
        global_data['initialization_error'] = str(e)
        logger.error(f"❌ Initialization failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

@app.get("/health")
async def health_check():
    """Health check with debug info"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "initialization_status": global_data['initialization_status'],
        "original_analyzer_available": original_analyzer_available,
        "debug_info": global_data.get('debug_info', {})
    }

@app.get("/data/status")
async def data_status():
    """Detailed data status"""
    return {
        "initialization_status": global_data['initialization_status'],
        "initialization_error": global_data.get('initialization_error'),
        "debug_info": global_data.get('debug_info', {}),
        "original_analyzer_available": original_analyzer_available,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/analyze/pitcher-vs-team")
async def analyze_pitcher_vs_team_debug(request: PredictionRequest):
    """Debug version of pitcher vs team analysis"""
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(status_code=503, detail=f"Data not ready: {global_data['initialization_status']}")
    
    logger.info(f"🔍 Starting analysis: {request.pitcher_name} vs {request.team}")
    
    master_data = global_data['master_player_data']
    if not master_data:
        raise HTTPException(status_code=500, detail="No master data available")
    
    # Debug: Find pitcher with detailed logging
    logger.info(f"🎯 Searching for pitcher: '{request.pitcher_name}'")
    pitcher_candidates = []
    pitcher_id = None
    
    for pid, pdata in master_data.items():
        roster_info = pdata.get('roster_info', {})
        if roster_info.get('type') == 'pitcher':
            name_resolved = roster_info.get('fullName_resolved', '')
            name_cleaned = roster_info.get('fullName_cleaned', '')
            name_short = roster_info.get('name', '')
            
            pitcher_candidates.append({
                'id': pid,
                'fullName_resolved': name_resolved,
                'fullName_cleaned': name_cleaned,
                'name': name_short,
                'team': roster_info.get('team', 'UNK')
            })
            
            # Check for exact match (case insensitive)
            if (name_resolved.lower() == request.pitcher_name.lower() or
                name_cleaned.lower() == request.pitcher_name.lower() or
                name_short.lower() == request.pitcher_name.lower()):
                pitcher_id = pid
                logger.info(f"✅ Found pitcher: {name_resolved} (ID: {pid})")
                break
    
    if not pitcher_id:
        logger.warning(f"❌ Pitcher '{request.pitcher_name}' not found")
        logger.info(f"📋 Available pitchers (first 10): {[p['fullName_resolved'] for p in pitcher_candidates[:10]]}")
        raise HTTPException(status_code=404, detail=f"Pitcher '{request.pitcher_name}' not found")
    
    # Debug: Find team batters with detailed logging
    logger.info(f"🏏 Searching for team '{request.team}' batters")
    team_batters = []
    team_candidates = []
    
    for pid, pdata in master_data.items():
        roster_info = pdata.get('roster_info', {})
        if roster_info.get('type') == 'hitter':
            team = roster_info.get('team', '')
            team_candidates.append(team)
            
            if team.upper() == request.team.upper():
                batter_name = roster_info.get('fullName_resolved', f"Player_{pid}")
                
                # Try to get real analysis if original analyzer is available
                if original_analyzer_available:
                    try:
                        # Call the real enhanced_hr_likelihood_score function
                        recent_stats = None  # Would need recent stats for full analysis
                        
                        analysis_result = enhanced_hr_likelihood_score(
                            batter_mlbam_id=pid,
                            pitcher_mlbam_id=pitcher_id,
                            master_player_data=master_data,
                            historical_data=global_data.get('historical_data', {}),
                            metric_ranges=global_data.get('metric_ranges', {}),
                            league_avg_stats=global_data.get('league_avg_stats', {}),
                            recent_batter_stats=recent_stats
                        )
                        
                        if analysis_result:
                            # Transform the real analysis result
                            team_batters.append({
                                'batter_name': batter_name,
                                'score': analysis_result.get('score', 50.0),
                                'confidence': 0.8,  # High confidence for real analysis
                                'data_source': 'enhanced_hr_likelihood_score',
                                'outcome_probabilities': analysis_result.get('outcome_probabilities', {
                                    'homerun': 5.0,
                                    'hit': 25.0,
                                    'reach_base': 30.0,
                                    'strikeout': 25.0
                                }),
                                # Include detailed fields from real analysis
                                'batter_hand': analysis_result.get('batter_hand'),
                                'pitcher_hand': analysis_result.get('pitcher_hand'),
                                'recent_avg': analysis_result.get('details', {}).get('recent_avg'),
                                'hr_rate': analysis_result.get('details', {}).get('hr_rate'),
                                'ab_due': analysis_result.get('details', {}).get('ab_due'),
                                'arsenal_matchup': analysis_result.get('matchup_components', {}).get('arsenal_matchup'),
                                'batter_overall': analysis_result.get('matchup_components', {}).get('batter_overall'),
                                'pitcher_overall': analysis_result.get('matchup_components', {}).get('pitcher_overall'),
                                'contextual': analysis_result.get('matchup_components', {}).get('contextual'),
                                'contact_trend': analysis_result.get('details', {}).get('contact_trend'),
                                'historical_summary': analysis_result.get('historical_summary'),
                                'recent_summary': analysis_result.get('recent_summary')
                            })
                        else:
                            raise ValueError("Analysis returned None")
                            
                    except Exception as analysis_error:
                        logger.error(f"Real analysis failed for {batter_name}: {analysis_error}")
                        # Fall back to mock data when real analysis fails
                        import random
                        team_batters.append({
                            'batter_name': batter_name,
                            'score': round(random.uniform(30, 85), 1),
                            'confidence': 0.5,
                            'data_source': 'fallback_after_analysis_error',
                            'outcome_probabilities': {
                                'homerun': round(random.uniform(2, 12), 1),
                                'hit': round(random.uniform(15, 35), 1),
                                'reach_base': round(random.uniform(20, 45), 1),
                                'strikeout': round(random.uniform(15, 35), 1)
                            },
                            'analysis_error': str(analysis_error)
                        })
                else:
                    team_batters.append({
                        'batter_name': batter_name,
                        'score': 40.0,
                        'confidence': 0.4,
                        'data_source': 'no_analyzer_available',
                        'outcome_probabilities': {
                            'homerun': 4.0,
                            'hit': 24.0,
                            'reach_base': 29.0,
                            'strikeout': 26.0
                        }
                    })
    
    unique_teams = list(set(team_candidates))
    logger.info(f"🏟️ Found {len(team_batters)} batters for team '{request.team}'")
    logger.info(f"📋 Available teams: {unique_teams[:20]}")  # Show first 20 teams
    
    if not team_batters:
        raise HTTPException(status_code=404, detail=f"No batters found for team '{request.team}'. Available teams: {unique_teams[:10]}")
    
    result = {
        'success': True,
        'pitcher_name': request.pitcher_name,
        'team': request.team.upper(),
        'predictions': team_batters[:request.max_results] if request.max_results else team_batters,
        'total_batters_analyzed': len(team_batters),
        'average_confidence': sum(b['confidence'] for b in team_batters) / len(team_batters),
        'primary_data_source': 'debug_analysis',
        'reliability': 'diagnostic',
        'debug_info': {
            'pitcher_candidates_count': len(pitcher_candidates),
            'team_candidates_count': len(unique_teams),
            'original_analyzer_available': original_analyzer_available
        }
    }
    
    logger.info(f"✅ Analysis complete: {len(team_batters)} predictions generated")
    return result

@app.get("/sort-options")
async def get_sort_options():
    """Sort options endpoint"""
    return {
        "options": [
            {"key": "score", "label": "HR Score", "description": "Overall HR likelihood"},
            {"key": "hr", "label": "HR Probability", "description": "HR probability %"},
            {"key": "hit", "label": "Hit Probability", "description": "Hit probability %"},
            {"key": "confidence", "label": "Confidence", "description": "Data quality"}
        ]
    }

if __name__ == "__main__":
    print("🔍 Starting Diagnostic Baseball API...")
    print("📊 This version provides detailed debugging information")
    
    uvicorn.run(
        "diagnostic_main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="debug"
    )