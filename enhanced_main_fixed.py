#!/usr/bin/env python3
"""
Enhanced FastAPI backend with improved missing data handling and fallback mechanisms.
This version includes fixes for Recent Trend Dir and AB Due field mapping.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import enhanced modules
from enhanced_data_handler import EnhancedDataHandler
from enhanced_analyzer import initialize_enhanced_analyzer, ENHANCED_WEIGHTS, SORTING_FACTORS
from config import DATA_DIR
from data_loader import load_all_data_files
from sort_utils import get_all_sort_options
from utils import find_player_id_by_name

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Enhanced Baseball Prediction API",
    description="MLB prediction system with robust missing data handling",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global data storage
global_data = {
    'enhanced_data_handler': None,
    'master_player_data': {},
    'name_to_player_id_map': {},
    'initialization_status': 'pending',
    'initialization_error': None,
    'last_updated': None
}

# Request/Response models
class PredictionRequest(BaseModel):
    pitcher_name: str
    team: str
    sort_by: str = "score"
    min_score: float = 0
    max_results: Optional[int] = None
    include_confidence: bool = True

class BulkPredictionRequest(BaseModel):
    matchups: List[Dict[str, str]]  # [{"pitcher_name": "X", "team": "Y"}, ...]
    sort_by: str = "score"
    limit: int = 10
    include_confidence: bool = True

class PlayerSearchRequest(BaseModel):
    name: str
    player_type: Optional[str] = None  # 'pitcher' or 'hitter'

class AnalysisReportRequest(BaseModel):
    predictions: List[Dict[str, Any]]
    include_summary: bool = True
    include_details: bool = True

# Helper function to transform predictions for UI compatibility
def transform_prediction_for_ui(prediction):
    """Transform API prediction to match UI expectations"""
    
    # Ensure we have the required nested structures
    if 'recent_N_games_raw_data' not in prediction:
        prediction['recent_N_games_raw_data'] = {}
    
    if 'trends_summary_obj' not in prediction['recent_N_games_raw_data']:
        prediction['recent_N_games_raw_data']['trends_summary_obj'] = {}
    
    if 'details' not in prediction:
        prediction['details'] = {}
    
    # 1. Fix Recent Trend Dir
    # Map p_trend_dir to the expected location
    if 'p_trend_dir' in prediction:
        prediction['recent_N_games_raw_data']['trends_summary_obj']['trend_direction'] = prediction['p_trend_dir']
        # Also add at top level for redundancy
        prediction['recent_trend_dir'] = prediction['p_trend_dir']
    
    # 2. Fix AB Due
    # Move ab_due from trends_summary_obj to details
    trends_obj = prediction['recent_N_games_raw_data']['trends_summary_obj']
    if 'ab_due' in trends_obj:
        prediction['details']['due_for_hr_ab_raw_score'] = trends_obj['ab_due']
        # Also add at top level for redundancy
        prediction['ab_due'] = trends_obj['ab_due']
    
    # 3. Add any other missing fields that the UI expects
    # Add default values if not present
    if 'trend_direction' not in prediction['recent_N_games_raw_data']['trends_summary_obj']:
        # Default to 'stable' if no trend data
        prediction['recent_N_games_raw_data']['trends_summary_obj']['trend_direction'] = 'stable'
        prediction['recent_trend_dir'] = 'stable'
    
    if 'due_for_hr_ab_raw_score' not in prediction['details']:
        # Default to 0 if no due factor
        prediction['details']['due_for_hr_ab_raw_score'] = 0
        prediction['ab_due'] = 0
    
    # 4. Ensure other expected fields exist with proper defaults
    # Add hits_due if present in trends
    if 'hits_due' in trends_obj:
        prediction['details']['due_for_hr_hits_raw_score'] = trends_obj.get('hits_due', 0)
        prediction['hits_due'] = trends_obj.get('hits_due', 0)
    
    return prediction

# Initialization function
async def initialize_enhanced_data():
    """Initialize enhanced data handling system"""
    try:
        global_data['initialization_status'] = 'loading'
        logger.info("Starting enhanced data initialization...")
        
        # Load all data files
        all_data = load_all_data_files()
        
        # Store master data
        global_data['master_player_data'] = all_data['master_player_data']
        global_data['name_to_player_id_map'] = all_data['name_to_player_id_map']
        
        # Initialize enhanced analyzer with league averages
        initialize_enhanced_analyzer(all_data['master_player_data'])
        
        # Create enhanced data handler
        global_data['enhanced_data_handler'] = EnhancedDataHandler(
            all_data['master_player_data'],
            all_data['daily_data'],
            all_data['name_to_player_id_map']
        )
        
        global_data['initialization_status'] = 'completed'
        global_data['last_updated'] = datetime.now()
        logger.info("Enhanced data initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize enhanced data: {e}")
        logger.error(traceback.format_exc())
        global_data['initialization_status'] = 'failed'
        global_data['initialization_error'] = str(e)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize data on startup"""
    await initialize_enhanced_data()

# Health check endpoints
@app.get("/")
async def root():
    """Root endpoint with system status"""
    return {
        "message": "Enhanced Baseball Prediction API",
        "status": global_data['initialization_status'],
        "version": "2.0.0",
        "features": [
            "Missing data handling",
            "League average fallbacks", 
            "Confidence scoring",
            "Team-based analysis",
            "Fixed field mapping for UI"
        ],
        "last_updated": global_data['last_updated'].isoformat() if global_data['last_updated'] else None
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(
            status_code=503,
            detail={
                "status": global_data['initialization_status'],
                "error": global_data['initialization_error']
            }
        )
    
    handler = global_data['enhanced_data_handler']
    return {
        "status": "healthy",
        "initialization": global_data['initialization_status'],
        "data_stats": {
            "total_players": len(global_data['master_player_data']),
            "analysis_stats": handler.analysis_stats if handler else {}
        },
        "last_updated": global_data['last_updated'].isoformat() if global_data['last_updated'] else None
    }

# Configuration endpoints
@app.get("/config/weights")
async def get_weights():
    """Get current analysis weights"""
    return {
        "enhanced_weights": ENHANCED_WEIGHTS,
        "available_factors": list(ENHANCED_WEIGHTS.keys())
    }

@app.get("/sort-options")
async def get_sort_options():
    """Get all available sorting options"""
    return {
        "options": get_all_sort_options(),
        "sorting_factors": SORTING_FACTORS
    }

# Data initialization endpoints
@app.post("/data/reinitialize")
async def reinitialize_data(background_tasks: BackgroundTasks):
    """Reinitialize data (useful for development)"""
    background_tasks.add_task(initialize_enhanced_data)
    return {"message": "Data reinitialization started", "status": "in_progress"}

# Enhanced prediction endpoints
@app.post("/analyze/pitcher-vs-team")
async def analyze_pitcher_vs_team(request: PredictionRequest):
    """
    Enhanced pitcher vs team analysis with missing data handling and field mapping fixes
    """
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(
            status_code=503, 
            detail=f"Data not ready. Status: {global_data['initialization_status']}"
        )
    
    try:
        handler = global_data['enhanced_data_handler']
        if not handler:
            raise HTTPException(status_code=500, detail="Enhanced data handler not available")
        
        # Perform enhanced analysis
        result = handler.analyze_team_matchup_with_fallbacks(
            pitcher_name=request.pitcher_name,
            team_abbr=request.team,
            sort_by=request.sort_by,
            min_score=request.min_score,
            include_confidence_metrics=request.include_confidence
        )
        
        if not result.get('success', False):
            raise HTTPException(status_code=404, detail=result.get('error', 'Analysis failed'))
        
        # Transform predictions to match UI expectations
        if result.get('predictions'):
            result['predictions'] = [
                transform_prediction_for_ui(pred) 
                for pred in result['predictions']
            ]
        
        # Limit results if requested
        if request.max_results and result.get('predictions'):
            result['predictions'] = result['predictions'][:request.max_results]
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in enhanced pitcher vs team analysis: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")

@app.post("/analyze/bulk-predictions")
async def bulk_predictions(request: BulkPredictionRequest):
    """
    Analyze multiple pitcher vs team matchups in bulk with field mapping fixes
    """
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(
            status_code=503,
            detail=f"Data not ready. Status: {global_data['initialization_status']}"
        )
    
    try:
        handler = global_data['enhanced_data_handler']
        if not handler:
            raise HTTPException(status_code=500, detail="Enhanced data handler not available")
        
        all_predictions = []
        matchup_summaries = []
        fallback_count = 0
        
        for matchup in request.matchups:
            try:
                result = handler.analyze_team_matchup_with_fallbacks(
                    pitcher_name=matchup['pitcher_name'],
                    team_abbr=matchup['team'],
                    sort_by='score',
                    min_score=0,
                    include_confidence_metrics=request.include_confidence
                )
                
                if result.get('success') and result.get('predictions'):
                    # Transform predictions for UI
                    transformed_predictions = [
                        transform_prediction_for_ui(pred) 
                        for pred in result['predictions']
                    ]
                    all_predictions.extend(transformed_predictions)
                    
                    # Track fallback usage
                    if result.get('used_fallback') or result.get('reliability') == 'low':
                        fallback_count += 1
                    
                    matchup_summaries.append({
                        'pitcher': matchup['pitcher_name'],
                        'team': matchup['team'],
                        'prediction_count': len(result['predictions']),
                        'avg_confidence': result.get('avg_confidence', 0),
                        'data_source': result.get('primary_data_source', 'unknown')
                    })
                    
            except Exception as e:
                logger.error(f"Failed to analyze matchup {matchup}: {e}")
                matchup_summaries.append({
                    'pitcher': matchup['pitcher_name'],
                    'team': matchup['team'],
                    'error': str(e)
                })
        
        # Sort all predictions
        if all_predictions:
            reverse_sort = request.sort_by not in ['strikeout']
            
            if request.sort_by == 'score':
                all_predictions.sort(key=lambda x: x.get('score', 0), reverse=reverse_sort)
            elif request.sort_by in ['hr', 'homerun']:
                all_predictions.sort(key=lambda x: x.get('outcome_probabilities', {}).get('homerun', 0), reverse=reverse_sort)
            elif request.sort_by == 'confidence':
                all_predictions.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            # Apply limit
            all_predictions = all_predictions[:request.limit]
        
        return {
            'success': True,
            'predictions': all_predictions,
            'total_predictions': len(all_predictions),
            'matchup_summaries': matchup_summaries,
            'batch_fallback_info': {
                'used_fallback': fallback_count > 0,
                'fallback_count': fallback_count,
                'successful_matchups': len([m for m in matchup_summaries if 'error' not in m])
            }
        }
        
    except Exception as e:
        logger.error(f"Error in bulk predictions: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Bulk analysis error: {str(e)}")

# Report generation endpoints
@app.post("/generate-report")
async def generate_analysis_report(request: AnalysisReportRequest):
    """Generate formatted analysis report from predictions"""
    try:
        from reporter import generate_analysis_report
        
        # Generate report
        analysis_result = {
            'predictions': request.predictions,
            'total_predictions': len(request.predictions)
        }
        
        formatted_report = generate_analysis_report(
            analysis_result,
            include_summary=request.include_summary,
            include_details=request.include_details
        )
        
        return {
            'report': formatted_report,
            'analysis_result': analysis_result,
            'formatted_report': formatted_report,
            'report_timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating analysis report: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")

# Player search endpoints
@app.post("/players/search")
async def search_players(request: PlayerSearchRequest):
    """Search for players by name"""
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(
            status_code=503, 
            detail=f"Data not ready. Status: {global_data['initialization_status']}"
        )
    
    try:
        master_data = global_data['master_player_data']
        name_to_id_map = global_data['name_to_player_id_map']
        
        # Search for player
        player_id = find_player_id_by_name(
            request.name, 
            request.player_type, 
            master_data, 
            name_to_id_map
        )
        
        if not player_id:
            # Fuzzy search for suggestions
            suggestions = []
            search_name_lower = request.name.lower()
            
            for pid, pdata in master_data.items():
                roster_info = pdata.get('roster_info', {})
                if request.player_type and roster_info.get('type') != request.player_type:
                    continue
                
                names_to_check = [
                    roster_info.get('fullName_resolved', ''),
                    roster_info.get('name_cleaned', ''),
                    roster_info.get('fullName_cleaned', '')
                ]
                
                for name in names_to_check:
                    if name and search_name_lower in name.lower():
                        suggestions.append({
                            'player_id': pid,
                            'name': roster_info.get('fullName_resolved', name),
                            'team': roster_info.get('team', 'UNK'),
                            'type': roster_info.get('type', 'unknown')
                        })
                        break
            
            return {
                'found': False,
                'suggestions': suggestions[:10],  # Limit suggestions
                'search_term': request.name
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
        
    except Exception as e:
        logger.error(f"Error in player search: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

# Legacy compatibility endpoints (fallback to original system)
@app.get("/legacy/pitcher-vs-team")
async def legacy_pitcher_vs_team(
    pitcher: str = Query(..., description="Pitcher name"),
    team: str = Query(..., description="Team abbreviation"),
    sort_by: str = Query("score", description="Sort field"),
    min_score: float = Query(0, description="Minimum score")
):
    """Legacy endpoint using original analysis system"""
    if global_data['initialization_status'] != 'completed':
        raise HTTPException(
            status_code=503, 
            detail=f"Data not ready. Status: {global_data['initialization_status']}"
        )
    
    try:
        # Import original analyzer as fallback
        from analyzer import analyze_matchup
        from data_loader import find_pitcher_by_name, get_team_hitters
        
        # Find pitcher
        pitcher_data = find_pitcher_by_name(
            pitcher, 
            global_data['master_player_data'], 
            global_data['name_to_player_id_map']
        )
        
        if not pitcher_data:
            raise HTTPException(status_code=404, detail=f"Pitcher '{pitcher}' not found")
        
        # Get team hitters
        hitters = get_team_hitters(team, global_data['master_player_data'])
        
        if not hitters:
            raise HTTPException(status_code=404, detail=f"No hitters found for team '{team}'")
        
        # Analyze each matchup
        predictions = []
        for hitter in hitters:
            try:
                result = analyze_matchup(
                    hitter, 
                    pitcher_data, 
                    global_data['master_player_data']
                )
                if result and result.get('score', 0) >= min_score:
                    # Transform for UI compatibility
                    predictions.append(transform_prediction_for_ui(result))
            except Exception as e:
                logger.error(f"Failed to analyze {hitter.get('name')} vs {pitcher}: {e}")
        
        # Sort results
        if sort_by == 'score':
            predictions.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return {
            'success': True,
            'predictions': predictions,
            'pitcher': pitcher,
            'team': team,
            'total_predictions': len(predictions),
            'data_source': 'legacy_analyzer'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in legacy analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Legacy analysis error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)