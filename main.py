#!/usr/bin/env python3
"""
FastAPI application for baseball home run prediction analysis
Converts the existing Python analysis system into a REST API
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


# Import your existing modules (adjust paths as needed)
try:
    from utils import find_player_id_by_name, clean_player_name, match_player_name_to_roster
    from data_loader import initialize_data, get_last_n_games_performance
    from analyzer import calculate_recent_trends, enhanced_hr_likelihood_score
    from reporter import format_prediction_result, format_detailed_matchup_report, process_matchup_batch_file, print_top_predictions
    from sort_utils import sort_predictions, get_sort_description
    from filter_utils import filter_predictions
    try:
        from hitter_filters import load_hitters_from_file, filter_predictions_by_hitters
        hitter_filtering_available = True
    except ImportError:
        hitter_filtering_available = False
except ImportError as e:
    print(f"Warning: Could not import analysis modules: {e}")
    print("Make sure all your Python analysis files are in the same directory or Python path")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Baseball HR Prediction API",
    description="API for baseball home run prediction and player analysis",
    version="1.0.0"
)

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://192.168.1.92:3000","http://localhost:3000", "http://localhost:5173"],  # Add your React dev server ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global data storage (initialized at startup)
app_data = {
    "master_player_data": None,
    "player_id_to_name_map": None,
    "name_to_player_id_map": None,
    "daily_game_data": None,
    "rosters_data": None,
    "historical_data": None,
    "league_avg_stats": None,
    "metric_ranges": None,
    "initialized": False
}

# Pydantic models for request/response (Pydantic 1.x compatible)
class PlayerPrediction(BaseModel):
    player_name: str
    player_id: Optional[str] = None
    team: str
    position: str = ""
    batter_hand: Optional[str] = None
    pitcher_hand: Optional[str] = None
    hr_score: float
    hr_probability: float  # Already as percentage
    hit_probability: float  # Already as percentage  
    reach_base_probability: float  # Already as percentage
    strikeout_probability: float  # Already as percentage
    recent_avg: float
    hr_rate: float
    obp: float
    ab_due: float
    hits_due: float
    heating_up: float
    cold: float
    arsenal_matchup: float
    batter_overall: float
    pitcher_overall: float
    historical_yoy_csv: float
    recent_daily_games: float
    contextual: float
    hitter_slg: Optional[float] = None
    pitcher_slg: Optional[float] = None
    
    # Additional fields from the analysis
    ab_since_last_hr: Optional[int] = None
    expected_ab_per_hr: Optional[float] = None
    h_since_last_hr: Optional[int] = None
    expected_h_per_hr: Optional[float] = None
    contact_trend: Optional[str] = None
    iso_2024: Optional[float] = None
    iso_2025: Optional[float] = None
    iso_trend: Optional[float] = None
    batter_pa_2025: Optional[int] = None
    ev_matchup_score: Optional[float] = None
    
    class Config:
        schema_extra = {
            "example": {
                "player_name": "Riley Greene",
                "team": "DET",
                "batter_hand": "L",
                "hr_score": 83.92,
                "hr_probability": 9.7,  # Already as percentage
                "hit_probability": 22.0,  # Already as percentage
                "recent_avg": 0.298,
                "ab_due": 5.9,
                "arsenal_matchup": 56.6
            }
        }

class PitcherVsTeamRequest(BaseModel):
    pitcher_name: str
    team_abbr: str
    sort_by: Optional[str] = "score"
    ascending: Optional[bool] = False
    limit: Optional[int] = 20
    detailed: Optional[bool] = False
    
    class Config:
        schema_extra = {
            "example": {
                "pitcher_name": "MacKenzie Gore",
                "team_abbr": "SEA",
                "sort_by": "hr",
                "limit": 20
            }
        }

class PitcherVsTeamResponse(BaseModel):
    pitcher_name: str
    team_abbr: str
    total_predictions: int
    predictions: List[PlayerPrediction]
    sort_info: Dict[str, Any]
    timestamp: str

class BatchMatchupRequest(BaseModel):
    matchups: List[Dict[str, str]]  # [{"pitcher_name": "...", "team_abbr": "..."}, ...]
    sort_by: Optional[str] = "score"
    ascending: Optional[bool] = False
    limit: Optional[int] = 20
    apply_filters: Optional[Dict[str, Any]] = None
    hitters_filter: Optional[List[str]] = None

class BatchMatchupResponse(BaseModel):
    total_matchups: int
    total_predictions: int
    combined_predictions: List[PlayerPrediction]
    matchup_summaries: List[Dict[str, Any]]
    timestamp: str

class FilterCriteria(BaseModel):
    trend: Optional[str] = None
    min_score: Optional[float] = None
    min_hr_prob: Optional[float] = None
    min_hit_prob: Optional[float] = None
    max_k_prob: Optional[float] = None
    contact_trend: Optional[str] = None
    min_due_ab: Optional[float] = None
    min_due_hits: Optional[float] = None

class PlayerSearchResponse(BaseModel):
    players: List[Dict[str, str]]
    total_found: int

# Helper functions
def convert_prediction_to_model(prediction_dict: dict) -> PlayerPrediction:
    """Convert internal prediction dictionary to Pydantic model"""
    try:
        # Extract basic info
        player_name = prediction_dict.get('batter_name', prediction_dict.get('player_name', ''))
        team = prediction_dict.get('batter_team', prediction_dict.get('team', ''))
        position = prediction_dict.get('position', '')
        batter_hand = prediction_dict.get('batter_hand', '')
        pitcher_hand = prediction_dict.get('pitcher_hand', '')
        
        # HR Score from top level
        hr_score = float(prediction_dict.get('score', 0))
        
        # Extract nested data
        details = prediction_dict.get('details', {})
        outcome_probabilities = prediction_dict.get('outcome_probabilities', {})
        matchup_components = prediction_dict.get('matchup_components', {})
        
        # Extract probabilities - these are already percentages, don't convert!
        hr_prob = float(outcome_probabilities.get('homerun', 0))  # Already as percentage
        hit_prob = float(outcome_probabilities.get('hit', 0))  # Already as percentage
        reach_base_prob = float(outcome_probabilities.get('reach_base', 0))  # Already as percentage
        strikeout_prob = float(outcome_probabilities.get('strikeout', 0))  # Already as percentage
        
        # Extract detailed fields from details object
        recent_avg = float(details.get('recent_avg', 0))
        hr_rate = float(details.get('hr_rate', 0))
        obp = float(details.get('obp', 0))
        
        # Due factors
        ab_due = float(details.get('due_for_hr_ab_raw_score', 0))
        hits_due = float(details.get('due_for_hr_hits_raw_score', 0))
        heating_up = float(details.get('heating_up_contact_raw_score', 0))
        cold = float(details.get('cold_batter_contact_raw_score', 0))
        
        # Component scores from matchup_components
        arsenal_matchup = float(matchup_components.get('arsenal_matchup', 0))
        batter_overall = float(matchup_components.get('batter_overall', 0))
        pitcher_overall = float(matchup_components.get('pitcher_overall', 0))
        historical_yoy_csv = float(matchup_components.get('historical_yoy_csv', 0))
        recent_daily_games = float(matchup_components.get('recent_daily_games', 0))
        contextual = float(matchup_components.get('contextual', 0))
        
        # Arsenal specific data
        arsenal_analysis = details.get('arsenal_analysis', {})
        overall_summary = arsenal_analysis.get('overall_summary_metrics', {}) if arsenal_analysis else {}
        hitter_slg = overall_summary.get('hitter_avg_slg') if overall_summary else None
        pitcher_slg = overall_summary.get('pitcher_avg_slg') if overall_summary else None
        
        # Additional detailed fields
        ab_since_last_hr = details.get('ab_since_last_hr')
        expected_ab_per_hr = details.get('expected_ab_per_hr')
        h_since_last_hr = details.get('h_since_last_hr')
        expected_h_per_hr = details.get('expected_h_per_hr')
        contact_trend = details.get('contact_trend')
        iso_2024 = details.get('iso_2024')
        iso_2025 = details.get('iso_2025_adj_for_trend')
        iso_trend = details.get('iso_trend_2025v2024')
        batter_pa_2025 = details.get('batter_pa_2025')
        ev_matchup_score = details.get('ev_matchup_raw_score')
        
        print(f"DEBUG: Fixed conversion for {player_name}:")
        print(f"  HR Score: {hr_score}")
        print(f"  HR Prob: {hr_prob}% (was showing as {hr_prob*100}% before)")
        print(f"  Hit Prob: {hit_prob}% (was showing as {hit_prob*100}% before)")
        print(f"  Batter Hand: {batter_hand}")
        print(f"  Recent Avg: {recent_avg}")
        print(f"  AB Due: {ab_due}")
        print(f"  Contact Trend: {contact_trend}")
        
        return PlayerPrediction(
            player_name=player_name,
            player_id=details.get('batter_id'),
            team=team,
            position=position,
            batter_hand=batter_hand,
            pitcher_hand=pitcher_hand,
            hr_score=hr_score,
            hr_probability=hr_prob,  # Already percentage
            hit_probability=hit_prob,  # Already percentage
            reach_base_probability=reach_base_prob,  # Already percentage
            strikeout_probability=strikeout_prob,  # Already percentage
            recent_avg=recent_avg,
            hr_rate=hr_rate,
            obp=obp,
            ab_due=ab_due,
            hits_due=hits_due,
            heating_up=heating_up,
            cold=cold,
            arsenal_matchup=arsenal_matchup,
            batter_overall=batter_overall,
            pitcher_overall=pitcher_overall,
            historical_yoy_csv=historical_yoy_csv,
            recent_daily_games=recent_daily_games,
            contextual=contextual,
            hitter_slg=hitter_slg,
            pitcher_slg=pitcher_slg,
            ab_since_last_hr=ab_since_last_hr,
            expected_ab_per_hr=expected_ab_per_hr,
            h_since_last_hr=h_since_last_hr,
            expected_h_per_hr=expected_h_per_hr,
            contact_trend=contact_trend,
            iso_2024=iso_2024,
            iso_2025=iso_2025,
            iso_trend=iso_trend,
            batter_pa_2025=batter_pa_2025,
            ev_matchup_score=ev_matchup_score
        )
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting prediction: {e}")
        logger.error(f"Prediction dict keys: {list(prediction_dict.keys())}")
        # Return a default prediction if conversion fails
        return PlayerPrediction(
            player_name=str(prediction_dict.get('batter_name', prediction_dict.get('player_name', 'Unknown'))),
            team=str(prediction_dict.get('batter_team', prediction_dict.get('team', ''))),
            position='',
            hr_score=float(prediction_dict.get('score', 0)),
            hr_probability=0.0, hit_probability=0.0,
            reach_base_probability=0.0, strikeout_probability=0.0,
            recent_avg=0.0, hr_rate=0.0, obp=0.0, ab_due=0.0,
            hits_due=0.0, heating_up=0.0, cold=0.0, arsenal_matchup=0.0,
            batter_overall=0.0, pitcher_overall=0.0, historical_yoy_csv=0.0,
            recent_daily_games=0.0, contextual=0.0
        )

def ensure_data_initialized():
    """Ensure data is initialized before processing requests"""
    if not app_data["initialized"]:
        raise HTTPException(status_code=503, detail="Data not initialized. Please wait for startup to complete.")

# Import the existing process_pitcher_vs_team function
def api_process_pitcher_vs_team(pitcher_name: str, team_abbr: str):
    """Wrapper around the existing process_pitcher_vs_team function"""
    ensure_data_initialized()
    
    try:
        # Import the function from your existing code
        # This assumes you have a function called process_pitcher_vs_team in your modules
        from debug_main import process_pitcher_vs_team
        
        predictions = process_pitcher_vs_team(
            pitcher_name, team_abbr,
            app_data["master_player_data"], 
            app_data["name_to_player_id_map"], 
            app_data["daily_game_data"],
            app_data["rosters_data"], 
            app_data["historical_data"], 
            app_data["league_avg_stats"], 
            app_data["metric_ranges"]
        )
        return predictions
    except Exception as e:
        logger.error(f"Error in api_process_pitcher_vs_team: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Baseball HR Prediction API",
        "version": "1.0.0",
        "initialized": app_data["initialized"],
        "endpoints": [
            "/health",
            "/pitcher-vs-team",
            "/batch-analysis",
            "/players/search",
            "/data/status"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "initialized": app_data["initialized"],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/data/status")
async def data_status():
    """Get data initialization status"""
    return {
        "initialized": app_data["initialized"],
        "players_loaded": len(app_data["master_player_data"]) if app_data["master_player_data"] else 0,
        "daily_games_loaded": len(app_data["daily_game_data"]) if app_data["daily_game_data"] else 0,
        "rosters_loaded": len(app_data["rosters_data"]) if app_data["rosters_data"] else 0
    }

@app.post("/data/reinitialize")
async def reinitialize_data(background_tasks: BackgroundTasks):
    """Reinitialize data (useful for development)"""
    background_tasks.add_task(initialize_app_data)
    return {"message": "Data reinitialization started"}

@app.get("/players/search")
async def search_players(
    query: str = Query(..., description="Player name to search for"),
    player_type: Optional[str] = Query(None, description="Filter by player type: 'pitcher' or 'batter'")
) -> PlayerSearchResponse:
    """Search for players by name"""
    ensure_data_initialized()
    
    try:
        found_players = []
        query_lower = query.lower()
        
        for player_id, player_data in app_data["master_player_data"].items():
            player_name = player_data.get('name', '')
            roster_info = player_data.get('roster_info', {})
            player_position_type = roster_info.get('type', '')
            
            if query_lower in player_name.lower():
                if not player_type or player_position_type == player_type:
                    found_players.append({
                        "player_id": player_id,
                        "name": player_name,
                        "type": player_position_type,
                        "team": roster_info.get('team', ''),
                        "position": roster_info.get('position', '')
                    })
        
        return PlayerSearchResponse(
            players=found_players[:50],  # Limit results
            total_found=len(found_players)
        )
    except Exception as e:
        logger.error(f"Error in search_players: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/pitcher-vs-team")
async def analyze_pitcher_vs_team(request: PitcherVsTeamRequest) -> PitcherVsTeamResponse:
    """Analyze a pitcher vs team matchup"""
    ensure_data_initialized()
    
    try:
        logger.info(f"Analyzing {request.pitcher_name} vs {request.team_abbr}")
        
        # Get predictions from your existing analysis
        raw_predictions = api_process_pitcher_vs_team(request.pitcher_name, request.team_abbr)
        
        print(f"DEBUG: Got {len(raw_predictions)} raw predictions")
        if raw_predictions:
            print(f"DEBUG: First raw prediction keys: {list(raw_predictions[0].keys())}")
            print(f"DEBUG: First raw prediction sample: {dict(list(raw_predictions[0].items())[:10])}")
        
        if not raw_predictions:
            raise HTTPException(status_code=404, detail="No predictions generated. Check pitcher name and team abbreviation.")
        
        # Sort predictions
        sorted_predictions = sort_predictions(
            raw_predictions, 
            sort_by=request.sort_by, 
            ascending=request.ascending
        )
        
        # Limit results
        if request.limit:
            sorted_predictions = sorted_predictions[:request.limit]
        
        print(f"DEBUG: After sorting and limiting: {len(sorted_predictions)} predictions")
        
        # Convert to Pydantic models
        prediction_models = [convert_prediction_to_model(pred) for pred in sorted_predictions]
        
        print(f"DEBUG: Converted to {len(prediction_models)} Pydantic models")
        if prediction_models:
            first_model = prediction_models[0]
            print(f"DEBUG: First model - Name: {first_model.player_name}, HR Score: {first_model.hr_score}, HR Prob: {first_model.hr_probability}")
        
        return PitcherVsTeamResponse(
            pitcher_name=request.pitcher_name,
            team_abbr=request.team_abbr,
            total_predictions=len(raw_predictions),
            predictions=prediction_models,
            sort_info={
                "sort_by": request.sort_by,
                "ascending": request.ascending,
                "description": get_sort_description(request.sort_by)
            },
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_pitcher_vs_team: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/batch-analysis")
async def batch_analysis(request: BatchMatchupRequest) -> BatchMatchupResponse:
    """Analyze multiple pitcher vs team matchups"""
    ensure_data_initialized()
    
    try:
        all_predictions = []
        matchup_summaries = []
        
        for matchup in request.matchups:
            pitcher_name = matchup.get("pitcher_name")
            team_abbr = matchup.get("team_abbr")
            
            if not pitcher_name or not team_abbr:
                continue
                
            try:
                raw_predictions = api_process_pitcher_vs_team(pitcher_name, team_abbr)
                
                if raw_predictions:
                    # Apply filters if provided
                    filtered_predictions = raw_predictions
                    if request.apply_filters:
                        filtered_predictions = filter_predictions(raw_predictions, request.apply_filters)
                    
                    # Apply hitter filtering if provided
                    if request.hitters_filter and hitter_filtering_available:
                        filtered_predictions = filter_predictions_by_hitters(
                            filtered_predictions, 
                            request.hitters_filter
                        )
                    
                    all_predictions.extend(filtered_predictions)
                    
                    matchup_summaries.append({
                        "pitcher_name": pitcher_name,
                        "team_abbr": team_abbr,
                        "predictions_count": len(filtered_predictions),
                        "status": "success"
                    })
                else:
                    matchup_summaries.append({
                        "pitcher_name": pitcher_name,
                        "team_abbr": team_abbr,
                        "predictions_count": 0,
                        "status": "no_predictions"
                    })
                    
            except Exception as e:
                logger.error(f"Error processing {pitcher_name} vs {team_abbr}: {e}")
                matchup_summaries.append({
                    "pitcher_name": pitcher_name,
                    "team_abbr": team_abbr,
                    "predictions_count": 0,
                    "status": "error",
                    "error": str(e)
                })
        
        # Sort all predictions
        if all_predictions:
            sorted_predictions = sort_predictions(
                all_predictions,
                sort_by=request.sort_by,
                ascending=request.ascending
            )
            
            # Limit results
            if request.limit:
                sorted_predictions = sorted_predictions[:request.limit]
            
            prediction_models = [convert_prediction_to_model(pred) for pred in sorted_predictions]
        else:
            prediction_models = []
        
        return BatchMatchupResponse(
            total_matchups=len(request.matchups),
            total_predictions=len(all_predictions),
            combined_predictions=prediction_models,
            matchup_summaries=matchup_summaries,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in batch_analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")

@app.get("/sort-options")
async def get_sort_options():
    """Get available sorting options"""
    sort_options = {
        'score': 'Overall HR Score',
        'hr': 'HR Probability',
        'homerun': 'HR Probability',
        'hit': 'Hit Probability',
        'reach_base': 'Reach Base Probability',
        'strikeout': 'Strikeout Probability (lowest first)',
        'arsenal_matchup': 'Arsenal Matchup Component',
        'batter_overall': 'Batter Overall Component',
        'pitcher_overall': 'Pitcher Overall Component',
        'historical_yoy_csv': 'Historical Trend Component',
        'recent_daily_games': 'Recent Performance Component',
        'contextual': 'Contextual Factors Component',
        'recent_avg': 'Recent Batting Average',
        'hr_rate': 'Recent HR Rate',
        'obp': 'Recent On-Base Percentage',
        'ab_due': 'Due for HR (AB-based)',
        'hits_due': 'Due for HR (hits-based)',
        'heating_up': 'Heating Up Contact Score',
        'cold': 'Cold Batter Score',
        'hitter_slg': 'Hitter SLG vs Arsenal',
        'pitcher_slg': 'Pitcher SLG Allowed'
    }
    
    return {"sort_options": sort_options}

# Startup event to initialize data
async def initialize_app_data():
    """Initialize the analysis data at startup"""
    try:
        logger.info("Initializing baseball analysis data...")
        
        # Set data path (adjust as needed)
        data_path = os.environ.get('BASEBALL_DATA_PATH', '../BaseballTracker/build/data')
        years = [2022, 2023, 2024, 2025]
        
        if not os.path.exists(data_path):
            logger.error(f"Data directory not found: {data_path}")
            return False
        
        # Initialize data using your existing function
        (
            master_player_data,
            player_id_to_name_map,
            name_to_player_id_map,
            daily_game_data,
            rosters_data,
            historical_data,
            league_avg_stats,
            metric_ranges
        ) = initialize_data(data_path, years)
        
        # Store in global app data
        app_data.update({
            "master_player_data": master_player_data,
            "player_id_to_name_map": player_id_to_name_map,
            "name_to_player_id_map": name_to_player_id_map,
            "daily_game_data": daily_game_data,
            "rosters_data": rosters_data,
            "historical_data": historical_data,
            "league_avg_stats": league_avg_stats,
            "metric_ranges": metric_ranges,
            "initialized": True
        })
        
        logger.info(f"Data initialization complete: {len(master_player_data)} players loaded")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize data: {e}")
        app_data["initialized"] = False
        return False

@app.on_event("startup")
async def startup_event():
    """Initialize data when the application starts"""
    await initialize_app_data()

if __name__ == "__main__":
    # For development
    uvicorn.run(
        "main:app",  # Replace "main" with your actual filename
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
