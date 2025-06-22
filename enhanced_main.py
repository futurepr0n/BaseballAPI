#!/usr/bin/env python3
"""
Enhanced FastAPI application for baseball analysis with missing data handling.
Provides robust analysis even when pitcher data is unavailable from Baseball Savant.
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
import subprocess

# Import enhanced modules
try:
    from utils import find_player_id_by_name, clean_player_name, match_player_name_to_roster
    from data_loader import initialize_data, get_last_n_games_performance
    from enhanced_analyzer import (
        calculate_league_averages_by_pitch_type,
        enhanced_arsenal_matchup_with_fallbacks,
        enhanced_hr_score_with_missing_data_handling
    )
    from enhanced_data_handler import EnhancedDataHandler, create_enhanced_analysis_report
    from sort_utils import sort_predictions, get_sort_description
    from filter_utils import filter_predictions
    
    # Import original modules as fallback
    from analyzer import calculate_recent_trends, enhanced_hr_likelihood_score
    from reporter import format_prediction_result, format_detailed_matchup_report
    
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all required Python files are available")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Enhanced Baseball HR Prediction API",
    description="Enhanced API with robust missing data handling for baseball analysis",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://192.168.1.92:3000","http://localhost:3000", "http://localhost:5173", "http://0.0.0.0:3000"],  # React development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Pydantic models
class PredictionRequest(BaseModel):
    pitcher_name: str
    team: str
    sort_by: Optional[str] = "score"
    min_score: Optional[float] = 0
    max_results: Optional[int] = None
    include_confidence: Optional[bool] = True

class BulkPredictionRequest(BaseModel):
    matchups: List[Dict[str, str]]  # [{"pitcher": "Name", "team": "ABC"}, ...]
    sort_by: Optional[str] = "score"
    min_score: Optional[float] = 0
    include_confidence: Optional[bool] = True

class DataQualityRequest(BaseModel):
    include_statistics: Optional[bool] = True
    include_recommendations: Optional[bool] = True

class PlayerSearchRequest(BaseModel):
    name: str
    player_type: Optional[str] = None  # "hitter" or "pitcher"

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize data on startup"""
    await initialize_enhanced_data()

async def initialize_enhanced_data():
    """Initialize the enhanced baseball analysis system"""
    try:
        global_data['initialization_status'] = 'in_progress'
        logger.info("Starting enhanced data initialization...")
        
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
        
        # Initialize enhanced data handler
        enhanced_handler = EnhancedDataHandler(
            master_player_data=master_player_data,
            league_avg_stats=league_avg_stats,
            metric_ranges=metric_ranges,
            daily_data=daily_game_data,
            roster_data=roster_data
        )
        
        global_data['enhanced_data_handler'] = enhanced_handler
        global_data['initialization_status'] = 'completed'
        
        logger.info(f"Enhanced data initialization completed successfully")
        logger.info(f"- Players loaded: {len(master_player_data)}")
        logger.info(f"- Daily game dates: {len(daily_game_data)}")
        logger.info(f"- Enhanced handler ready with fallback strategies")
        
    except Exception as e:
        global_data['initialization_status'] = 'failed'
        global_data['initialization_error'] = str(e)
        logger.error(f"Enhanced data initialization failed: {e}")
        logger.error(traceback.format_exc())

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0-enhanced"
    }

@app.get("/data/status")
async def data_status():
    """Check data initialization status"""
    status = global_data['initialization_status']
    
    response = {
        "initialization_status": status,
        "timestamp": datetime.now().isoformat()
    }
    
    if status == 'completed':
        response.update({
            "players_loaded": len(global_data.get('master_player_data', {})),
            "daily_game_dates": len(global_data.get('daily_game_data', {})),
            "enhanced_features": True,
            "fallback_strategies": [
                "league_average_fallbacks",
                "team_based_estimates", 
                "position_based_profiles",
                "confidence_adjustments"
            ]
        })
        
        # Get enhanced handler statistics if available
        handler = global_data.get('enhanced_data_handler')
        if handler:
            response["analysis_statistics"] = handler.get_analysis_statistics()
    
    elif status == 'failed':
        response["error"] = global_data.get('initialization_error')
    
    return response

@app.post("/data/reinitialize")
async def reinitialize_data(background_tasks: BackgroundTasks):
    """Reinitialize data (useful for development)"""
    background_tasks.add_task(initialize_enhanced_data)
    return {"message": "Data reinitialization started", "status": "in_progress"}

# Enhanced prediction endpoints
@app.post("/analyze/pitcher-vs-team")
async def analyze_pitcher_vs_team(request: PredictionRequest):
    """
    Enhanced pitcher vs team analysis with missing data handling
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
        
        # Limit results if requested
        if request.max_results and result.get('predictions'):
            result['predictions'] = result['predictions'][:request.max_results]
            result['total_shown'] = len(result['predictions'])
        
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
    Analyze multiple pitcher vs team matchups in bulk
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
        
        results = []
        total_analyses = 0
        successful_analyses = 0
        
        for matchup in request.matchups:
            pitcher_name = matchup.get('pitcher', '').strip()
            team = matchup.get('team', '').strip()
            
            if not pitcher_name or not team:
                results.append({
                    'pitcher_name': pitcher_name,
                    'team': team,
                    'success': False,
                    'error': 'Missing pitcher name or team'
                })
                continue
            
            total_analyses += 1
            
            try:
                result = handler.analyze_team_matchup_with_fallbacks(
                    pitcher_name=pitcher_name,
                    team_abbr=team,
                    sort_by=request.sort_by,
                    min_score=request.min_score,
                    include_confidence_metrics=request.include_confidence
                )
                
                if result.get('success', False):
                    successful_analyses += 1
                
                results.append(result)
                
            except Exception as e:
                results.append({
                    'pitcher_name': pitcher_name,
                    'team': team,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'total_matchups_requested': len(request.matchups),
            'total_analyses_attempted': total_analyses,
            'successful_analyses': successful_analyses,
            'success_rate': round(successful_analyses / total_analyses * 100, 1) if total_analyses > 0 else 0,
            'results': results,
            'sort_by': request.sort_by,
            'min_score_filter': request.min_score
        }
        
    except Exception as e:
        logger.error(f"Error in bulk predictions: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk analysis error: {str(e)}")

@app.get("/analyze/data-quality")
async def get_data_quality_info(include_stats: bool = Query(True), include_recommendations: bool = Query(True)):
    """
    Get information about data quality and missing data handling
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
        
        response = {
            'timestamp': datetime.now().isoformat(),
            'enhanced_features_active': True,
            'fallback_strategies': [
                'Real-time league averages by pitch type',
                'Team-based pitching profiles',
                'Position-based estimates (starter/reliever)',
                'Dynamic component weight adjustment',
                'Confidence-based score adjustments'
            ]
        }
        
        if include_stats:
            response['analysis_statistics'] = handler.get_analysis_statistics()
        
        if include_recommendations:
            stats = handler.get_analysis_statistics()
            if 'recommendations' in stats:
                response['recommendations'] = stats['recommendations']
        
        # Add league average information
        response['league_averages_info'] = {
            'pitch_types_covered': len(handler.league_avg_by_pitch_type),
            'real_time_calculation': True,
            'fallback_to_defaults': 'when_insufficient_data'
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting data quality info: {e}")
        raise HTTPException(status_code=500, detail=f"Data quality error: {str(e)}")


@app.get("/sort-options")
async def get_sort_options():
    """
    Get available sorting options for predictions
    """
    return {
        "options": [
            # Core Scores
            {
                "key": "score",
                "label": "Overall HR Score", 
                "description": "Overall home run likelihood score (0-100)"
            },
            {
                "key": "hr",
                "label": "HR Probability",
                "description": "Home run probability percentage"
            },
            {
                "key": "hr_probability",
                "label": "HR Probability (Alt)",
                "description": "Home run probability percentage (alternative key)"
            },
            {
                "key": "hit", 
                "label": "Hit Probability",
                "description": "Hit probability percentage"
            },
            {
                "key": "hit_probability", 
                "label": "Hit Probability (Alt)",
                "description": "Hit probability percentage (alternative key)"
            },
            {
                "key": "reach_base",
                "label": "Reach Base Probability", 
                "description": "Reach base probability percentage"
            },
            {
                "key": "reach_base_probability",
                "label": "Reach Base Probability (Alt)",
                "description": "Reach base probability percentage (alternative key)"
            },
            {
                "key": "strikeout",
                "label": "Strikeout Probability",
                "description": "Strikeout probability (lower is better)"
            },
            {
                "key": "strikeout_probability",
                "label": "Strikeout Probability (Alt)",
                "description": "Strikeout probability (lower is better, alternative key)"
            },
            {
                "key": "confidence",
                "label": "Confidence",
                "description": "Data quality confidence level (0.0-1.0)"
            },
            {
                "key": "enhanced_confidence",
                "label": "Enhanced Confidence", 
                "description": "Enhanced confidence with dashboard context boost"
            },
            {
                "key": "standout_score",
                "label": "Standout Score",
                "description": "Enhanced HR score with dashboard context"
            },
            
            # Component Scores
            {
                "key": "arsenal",
                "label": "Arsenal Matchup",
                "description": "Arsenal matchup component score"
            },
            {
                "key": "arsenal_matchup",
                "label": "Arsenal Matchup (Alt)",
                "description": "Arsenal matchup component score (alternative key)"
            },
            {
                "key": "batter",
                "label": "Batter Overall",
                "description": "Batter overall component score"
            },
            {
                "key": "batter_overall",
                "label": "Batter Overall (Alt)",
                "description": "Batter overall component score (alternative key)"
            },
            {
                "key": "pitcher",
                "label": "Pitcher Overall",
                "description": "Pitcher overall component score"
            },
            {
                "key": "pitcher_overall",
                "label": "Pitcher Overall (Alt)",
                "description": "Pitcher overall component score (alternative key)"
            },
            {
                "key": "historical",
                "label": "Historical Trend",
                "description": "Historical trend component score"
            },
            {
                "key": "historical_yoy_csv",
                "label": "Historical Trend (Alt)",
                "description": "Historical trend component score (alternative key)"
            },
            {
                "key": "recent",
                "label": "Recent Performance",
                "description": "Recent performance component score"
            },
            {
                "key": "recent_daily_games",
                "label": "Recent Performance (Alt)",
                "description": "Recent performance component score (alternative key)"
            },
            {
                "key": "contextual",
                "label": "Contextual Factors",
                "description": "Contextual factors component score"
            },
            
            # Recent Performance Stats
            {
                "key": "recent_avg",
                "label": "Recent Batting Average",
                "description": "Recent batting average"
            },
            {
                "key": "avg",
                "label": "Recent Batting Average (Alt)",
                "description": "Recent batting average (alternative key)"
            },
            {
                "key": "recent_hr_rate",
                "label": "Recent HR Rate",
                "description": "Recent home run rate"
            },
            {
                "key": "hr_rate",
                "label": "Recent HR Rate (Alt)",
                "description": "Recent home run rate (alternative key)"
            },
            {
                "key": "recent_obp",
                "label": "Recent On-Base Percentage",
                "description": "Recent on-base percentage"
            },
            {
                "key": "obp",
                "label": "Recent On-Base Percentage (Alt)",
                "description": "Recent on-base percentage (alternative key)"
            },
            
            # Due Factors & Trends
            {
                "key": "due_ab",
                "label": "Due for HR (AB-based)",
                "description": "Due for home run based on at-bats"
            },
            {
                "key": "ab_due",
                "label": "Due for HR (AB-based Alt)",
                "description": "Due for home run based on at-bats (alternative key)"
            },
            {
                "key": "due_hits",
                "label": "Due for HR (Hits-based)",
                "description": "Due for home run based on hits"
            },
            {
                "key": "hits_due",
                "label": "Due for HR (Hits-based Alt)",
                "description": "Due for home run based on hits (alternative key)"
            },
            {
                "key": "contact_heat",
                "label": "Heating Up Contact",
                "description": "Heating up contact score"
            },
            {
                "key": "heating_up",
                "label": "Heating Up Contact (Alt)",
                "description": "Heating up contact score (alternative key)"
            },
            {
                "key": "cold",
                "label": "Cold Batter Score",
                "description": "Cold batter score (higher = more concerning)"
            },
            
            # Arsenal Analysis
            {
                "key": "hitter_slg",
                "label": "Hitter SLG vs Arsenal",
                "description": "Hitter slugging percentage vs pitcher's arsenal"
            },
            {
                "key": "pitcher_slg",
                "label": "Pitcher SLG Allowed",
                "description": "Pitcher slugging percentage allowed"
            }
        ]
    }

@app.post("/analyze/generate-report")
async def generate_analysis_report(request: PredictionRequest):
    """
    Generate a detailed analysis report with data quality information
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
        
        # Perform analysis
        analysis_result = handler.analyze_team_matchup_with_fallbacks(
            pitcher_name=request.pitcher_name,
            team_abbr=request.team,
            sort_by=request.sort_by,
            min_score=request.min_score,
            include_confidence_metrics=True
        )
        
        if not analysis_result.get('success', False):
            raise HTTPException(status_code=404, detail=analysis_result.get('error', 'Analysis failed'))
        
        # Generate formatted report
        formatted_report = create_enhanced_analysis_report(analysis_result)
        
        return {
            'success': True,
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
        # Use original analysis system as fallback
        # This would require implementing the original process_pitcher_vs_team function
        return {
            'message': 'Legacy endpoint - use /analyze/pitcher-vs-team for enhanced analysis',
            'pitcher': pitcher,
            'team': team,
            'recommendation': 'Switch to enhanced endpoints for better missing data handling'
        }
        
    except Exception as e:
        logger.error(f"Error in legacy analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Legacy analysis error: {str(e)}")

@app.post("/refresh-lineups")
async def refresh_lineups():
    """
    Fetch fresh starting lineup data from MLB Stats API and MLB.com
    Runs both fetch_starting_lineups.py (for pitcher data) and enhanced_lineup_scraper.py (for batting orders)
    """
    try:
        logger.info("🔄 Starting lineup refresh request")
        
        # Path to the baseball scraper script (relative to current working directory)
        scraper_dir = "../BaseballScraper"
        venv_python_path = "venv/bin/python"
        
        # Check if we can use the venv python from the scraper directory
        full_venv_path = os.path.join(scraper_dir, venv_python_path)
        if os.path.exists(full_venv_path):
            python_cmd = venv_python_path  # Use relative path within scraper_dir
        else:
            python_cmd = "python3"  # Fallback to system python
        
        # Set environment to prevent .pyc files and use venv
        env = os.environ.copy()
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        
        # Step 1: Run fetch_starting_lineups.py (for pitcher data and game info)
        script_path = "fetch_starting_lineups.py"
        logger.info(f"🐍 Step 1: Executing {python_cmd} {script_path} (cwd: {scraper_dir})")
        
        result1 = subprocess.run(
            [python_cmd, script_path],
            cwd=scraper_dir,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            env=env
        )
        
        games_found = 0
        lineups_found = 0
        
        if result1.returncode == 0:
            logger.info("✅ Step 1: Basic lineup data fetch completed successfully")
            
            # Parse output for game count
            output1 = result1.stdout
            for line in output1.split('\n'):
                if "Found" in line and "games" in line:
                    try:
                        parts = line.split()
                        games_found = int([p for p in parts if p.isdigit()][0])
                    except:
                        pass
                if "having lineup info" in line:
                    try:
                        parts = line.split()
                        lineups_found = int([p for p in parts if p.isdigit()][1])
                    except:
                        pass
        else:
            logger.error(f"❌ Step 1 failed with return code {result1.returncode}")
            return {
                "success": False,
                "message": "Basic lineup fetch failed",
                "error": result1.stderr.strip() or result1.stdout.strip()
            }
        
        # Step 2: Run enhanced_lineup_scraper.py (for batting orders) if available
        enhanced_script_path = "enhanced_lineup_scraper.py"
        enhanced_script_full_path = os.path.join(scraper_dir, enhanced_script_path)
        
        enhanced_output = ""
        enhanced_success = False
        
        if os.path.exists(enhanced_script_full_path):
            logger.info(f"🐍 Step 2: Executing {python_cmd} {enhanced_script_path} (cwd: {scraper_dir})")
            
            result2 = subprocess.run(
                [python_cmd, enhanced_script_path],
                cwd=scraper_dir,
                capture_output=True,
                text=True,
                timeout=180,  # 3 minute timeout for web scraping
                env=env
            )
            
            if result2.returncode == 0:
                logger.info("✅ Step 2: Enhanced batting order fetch completed successfully")
                enhanced_output = result2.stdout
                enhanced_success = True
            else:
                logger.warning(f"⚠️ Step 2: Enhanced scraper failed (return code {result2.returncode})")
                enhanced_output = f"Enhanced scraper failed: {result2.stderr.strip() or result2.stdout.strip()}"
        else:
            logger.info("ℹ️ Step 2: Enhanced lineup scraper not found, skipping batting order extraction")
            enhanced_output = "Enhanced lineup scraper not available"
        
        # Combine results
        combined_output = f"=== BASIC LINEUP FETCH ===\n{result1.stdout.strip()}"
        if enhanced_success:
            combined_output += f"\n\n=== ENHANCED BATTING ORDERS ===\n{enhanced_output.strip()}"
        else:
            combined_output += f"\n\n=== ENHANCED SCRAPER STATUS ===\n{enhanced_output}"
        
        return {
            "success": True,
            "message": "Lineup refresh completed" + (" with batting orders" if enhanced_success else " (basic data only)"),
            "timestamp": datetime.now().isoformat(),
            "games_found": games_found,
            "lineups_found": lineups_found,
            "enhanced_lineups": enhanced_success,
            "output": combined_output
        }
            
    except subprocess.TimeoutExpired:
        logger.error("⏰ Lineup refresh timed out")
        raise HTTPException(status_code=408, detail="Lineup refresh timed out")
    
    except Exception as e:
        logger.error(f"❌ Lineup refresh error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh lineups: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Baseball Analysis API")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    print("🚀 Starting Enhanced Baseball Analysis API...")
    print(f"🔗 API will be available at: http://{args.host}:{args.port}")
    print(f"📚 Documentation at: http://{args.host}:{args.port}/docs")
    print("⚡ Enhanced features: Missing data fallbacks, confidence scoring, team-based estimates")
    
    uvicorn.run(
        "enhanced_main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )