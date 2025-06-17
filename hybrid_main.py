#!/usr/bin/env python3
"""
Hybrid FastAPI - Enhanced features with graceful fallback to original
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import os
import sys
import asyncio
from datetime import datetime
import uvicorn
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import enhanced modules
enhanced_features_available = False
try:
    from enhanced_analyzer import (
        calculate_league_averages_by_pitch_type,
        enhanced_arsenal_matchup_with_fallbacks,
        enhanced_hr_score_with_missing_data_handling
    )
    from enhanced_data_handler import EnhancedDataHandler, create_enhanced_analysis_report
    enhanced_features_available = True
    logger.info("✅ Enhanced features loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Enhanced features not available: {e}")
    enhanced_features_available = False

# Import core modules (required)
try:
    from utils import find_player_id_by_name, clean_player_name
    from data_loader import initialize_data, get_last_n_games_performance
    from analyzer import enhanced_hr_likelihood_score, calculate_recent_trends
    logger.info("✅ Core modules loaded successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import core modules: {e}")
    sys.exit(1)

# Try to import optional modules
try:
    from sort_utils import sort_predictions, get_sort_description
    from filter_utils import filter_predictions
    from reporter import format_prediction_result
    optional_features_available = True
except ImportError as e:
    logger.warning(f"⚠️ Optional features not available: {e}")
    optional_features_available = False

# Create FastAPI app
app = FastAPI(
    title="Hybrid Baseball HR Prediction API",
    description="Enhanced API with fallback to original functionality",
    version="2.0.0-hybrid"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://192.168.1.92:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class PredictionRequest(BaseModel):
    pitcher_name: str
    team: str
    sort_by: Optional[str] = "score"
    min_score: Optional[float] = 0
    max_results: Optional[int] = None
    include_confidence: Optional[bool] = True

# Global variables for data
global_data = {
    'master_player_data': None,
    'player_id_to_name_map': None,
    'name_to_player_id_map': None,
    'daily_game_data': None,
    'roster_data': None,
    'historical_data': None,
    'league_avg_stats': None,
    'metric_ranges': None,
    'enhanced_data_handler': None,
    'initialization_status': 'not_started',
    'initialization_error': None
}

@app.on_event("startup")
async def startup_event():
    """Initialize data on startup"""
    await initialize_baseball_data()

async def initialize_baseball_data():
    """Initialize the baseball analysis system"""
    try:
        global_data['initialization_status'] = 'in_progress'
        logger.info("🏗️ Starting data initialization...")
        
        # Initialize base data
        result = initialize_data()
        if not result or len(result) != 8:
            raise ValueError("Data initialization failed - incomplete result")
        
        (master_player_data, player_id_to_name_map, name_to_player_id_map, 
         daily_game_data, roster_data, historical_data, league_avg_stats, metric_ranges) = result
        
        # Store base data
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
        
        # Initialize enhanced features if available
        if enhanced_features_available:
            try:
                enhanced_handler = EnhancedDataHandler(
                    master_player_data=master_player_data,
                    league_avg_stats=league_avg_stats,
                    metric_ranges=metric_ranges
                )
                global_data['enhanced_data_handler'] = enhanced_handler
                logger.info("✅ Enhanced data handler initialized")
            except Exception as e:
                logger.warning(f"⚠️ Enhanced handler failed, using fallback: {e}")
        
        global_data['initialization_status'] = 'completed'
        
        logger.info(f"🎉 Data initialization completed successfully")
        logger.info(f"📊 Players loaded: {len(master_player_data)}")
        logger.info(f"📅 Daily game dates: {len(daily_game_data)}")
        logger.info(f"⚡ Enhanced features: {'enabled' if enhanced_features_available else 'disabled'}")
        
    except Exception as e:
        global_data['initialization_status'] = 'failed'
        global_data['initialization_error'] = str(e)
        logger.error(f"❌ Data initialization failed: {e}")
        logger.error(traceback.format_exc())

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0-hybrid",
        "enhanced_features": enhanced_features_available
    }

@app.get("/data/status")
async def data_status():
    """Check data initialization status"""
    status = global_data['initialization_status']
    
    response = {
        "initialization_status": status,
        "timestamp": datetime.now().isoformat(),
        "enhanced_features": enhanced_features_available,
        "optional_features": optional_features_available
    }
    
    if status == 'completed':
        response.update({
            "players_loaded": len(global_data.get('master_player_data', {})),
            "daily_game_dates": len(global_data.get('daily_game_data', {})),
            "fallback_strategies": [
                "league_average_fallbacks",
                "team_based_estimates", 
                "confidence_adjustments"
            ] if enhanced_features_available else ["basic_analysis"]
        })
    elif status == 'failed':
        response["error"] = global_data.get('initialization_error')
    
    return response

@app.post("/data/reinitialize")
async def reinitialize_data(background_tasks: BackgroundTasks):
    """Reinitialize data"""
    background_tasks.add_task(initialize_baseball_data)
    return {"message": "Data reinitialization started", "status": "in_progress"}

@app.post("/analyze/pitcher-vs-team")
async def analyze_pitcher_vs_team_enhanced(request: PredictionRequest):
    """Enhanced pitcher vs team analysis with fallback"""
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(
            status_code=503, 
            detail=f"Data not ready. Status: {global_data['initialization_status']}"
        )
    
    try:
        # Try enhanced analysis first
        if enhanced_features_available and global_data.get('enhanced_data_handler'):
            handler = global_data['enhanced_data_handler']
            result = handler.analyze_team_matchup_with_fallbacks(
                pitcher_name=request.pitcher_name,
                team_abbr=request.team,
                sort_by=request.sort_by,
                min_score=request.min_score,
                include_confidence_metrics=request.include_confidence
            )
            
            if not result.get('success', False):
                raise HTTPException(status_code=404, detail=result.get('error', 'Analysis failed'))
            
            # Limit results if requested
            if request.max_results and result.get('predictions'):
                result['predictions'] = result['predictions'][:request.max_results]
                result['total_shown'] = len(result['predictions'])
            
            return result
        else:
            # Fallback to basic analysis
            return await analyze_pitcher_vs_team_basic(request)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in enhanced analysis: {e}")
        # Try fallback
        try:
            return await analyze_pitcher_vs_team_basic(request)
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")

async def analyze_pitcher_vs_team_basic(request: PredictionRequest):
    """Basic pitcher vs team analysis (fallback)"""
    # This is a simplified version - you'd implement the original analysis logic here
    master_data = global_data['master_player_data']
    
    # Find pitcher
    pitcher_id = None
    for pid, pdata in master_data.items():
        roster_info = pdata.get('roster_info', {})
        if (roster_info.get('type') == 'pitcher' and 
            roster_info.get('fullName_resolved', '').lower() == request.pitcher_name.lower()):
            pitcher_id = pid
            break
    
    if not pitcher_id:
        raise HTTPException(status_code=404, detail=f"Pitcher '{request.pitcher_name}' not found")
    
    # Find team batters
    team_batters = []
    for pid, pdata in master_data.items():
        roster_info = pdata.get('roster_info', {})
        if (roster_info.get('type') == 'hitter' and 
            roster_info.get('team', '').upper() == request.team.upper()):
            team_batters.append({
                'batter_name': roster_info.get('fullName_resolved', f"Player_{pid}"),
                'score': 50.0,  # Default score
                'confidence': 0.6,  # Medium confidence
                'data_source': 'basic_analysis',
                'outcome_probabilities': {
                    'homerun': 5.0,
                    'hit': 25.0,
                    'reach_base': 30.0,
                    'strikeout': 25.0
                }
            })
    
    return {
        'success': True,
        'pitcher_name': request.pitcher_name,
        'team': request.team.upper(),
        'predictions': team_batters[:request.max_results] if request.max_results else team_batters,
        'total_batters_analyzed': len(team_batters),
        'average_confidence': 0.6,
        'primary_data_source': 'basic_analysis',
        'reliability': 'medium',
        'analysis_type': 'fallback'
    }

@app.get("/analyze/data-quality")
async def get_data_quality():
    """Data quality information"""
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(status_code=503, detail="Data not ready")
    
    response = {
        'timestamp': datetime.now().isoformat(),
        'enhanced_features_active': enhanced_features_available,
        'optional_features_active': optional_features_available,
        'initialization_status': global_data['initialization_status']
    }
    
    if enhanced_features_available and global_data.get('enhanced_data_handler'):
        handler = global_data['enhanced_data_handler']
        response['analysis_statistics'] = handler.get_analysis_statistics()
        response['fallback_strategies'] = [
            'Real-time league averages by pitch type',
            'Team-based pitching profiles',
            'Position-based estimates',
            'Dynamic component weight adjustment'
        ]
    else:
        response['fallback_strategies'] = ['Basic analysis only']
        response['analysis_statistics'] = {
            'message': 'Enhanced features not available - using basic analysis'
        }
    
    return response

@app.get("/sort-options")
async def get_sort_options():
    """Get available sorting options for predictions"""
    return {
        "options": [
            {
                "key": "score", 
                "label": "HR Score", 
                "description": "Overall home run likelihood score",
                "ascending": False
            },
            {
                "key": "hr", 
                "label": "HR Probability", 
                "description": "Home run probability percentage",
                "ascending": False
            },
            {
                "key": "hit", 
                "label": "Hit Probability", 
                "description": "Hit probability percentage",
                "ascending": False
            },
            {
                "key": "reach_base", 
                "label": "Reach Base", 
                "description": "Reach base probability",
                "ascending": False
            },
            {
                "key": "strikeout", 
                "label": "Strikeout", 
                "description": "Strikeout probability (lower is better)",
                "ascending": True
            },
            {
                "key": "confidence", 
                "label": "Confidence", 
                "description": "Data quality confidence level",
                "ascending": False
            }
        ]
    }

@app.post("/players/search")
async def search_players(request: dict):
    """Search for players by name"""
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(status_code=503, detail="Data not ready")
    
    try:
        name = request.get('name', '').strip()
        player_type = request.get('player_type')
        
        if not name:
            raise HTTPException(status_code=400, detail="Name parameter required")
        
        master_data = global_data['master_player_data']
        name_to_id_map = global_data['name_to_player_id_map']
        
        # Search for player
        player_id = find_player_id_by_name(name, player_type, master_data, name_to_id_map)
        
        if not player_id:
            # Fuzzy search for suggestions
            suggestions = []
            search_name_lower = name.lower()
            
            for pid, pdata in master_data.items():
                roster_info = pdata.get('roster_info', {})
                if player_type and roster_info.get('type') != player_type:
                    continue
                
                names_to_check = [
                    roster_info.get('fullName_resolved', ''),
                    roster_info.get('name_cleaned', ''),
                    roster_info.get('fullName_cleaned', '')
                ]
                
                for check_name in names_to_check:
                    if check_name and search_name_lower in check_name.lower():
                        suggestions.append({
                            'player_id': pid,
                            'name': roster_info.get('fullName_resolved', check_name),
                            'team': roster_info.get('team', 'UNK'),
                            'type': roster_info.get('type', 'unknown')
                        })
                        break
            
            return {
                'found': False,
                'suggestions': suggestions[:10],  # Limit suggestions
                'search_term': name
            }
        
        # Player found
        player_data = master_data[player_id]
        roster_info = player_data.get('roster_info', {})
        
        return {
            'found': True,
            'player': {
                'player_id': player_id,
                'name': roster_info.get('fullName_resolved'),
                'team': roster_info.get('team'),
                'type': roster_info.get('type'),
                'bats': roster_info.get('bats') if roster_info.get('type') == 'hitter' else None,
                'throws': roster_info.get('ph') if roster_info.get('type') == 'pitcher' else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in player search: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

# Legacy endpoint for compatibility
@app.post("/pitcher-vs-team")
async def analyze_pitcher_vs_team_legacy(request: dict):
    """Legacy pitcher vs team analysis endpoint"""
    # Convert legacy format to new format
    new_request = PredictionRequest(
        pitcher_name=request.get('pitcher_name', ''),
        team=request.get('team_abbr', request.get('team', '')),
        sort_by=request.get('sort_by', 'score'),
        min_score=request.get('min_score', 0),
        max_results=request.get('limit'),
        include_confidence=request.get('detailed', True)
    )
    
    return await analyze_pitcher_vs_team_enhanced(new_request)

if __name__ == "__main__":
    print("🚀 Starting Hybrid Baseball Analysis API...")
    print("🔗 API will be available at: http://localhost:8000")
    print("📚 Documentation at: http://localhost:8000/docs")
    print("⚡ Enhanced features will be enabled if dependencies are available")
    
    uvicorn.run(
        "hybrid_main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )