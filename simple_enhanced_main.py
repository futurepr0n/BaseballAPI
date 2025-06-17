#!/usr/bin/env python3
"""
Simplified Enhanced FastAPI for debugging connection issues
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

# Create FastAPI app
app = FastAPI(
    title="Enhanced Baseball HR Prediction API",
    description="Enhanced API with robust missing data handling",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple models
class PredictionRequest(BaseModel):
    pitcher_name: str
    team: str
    sort_by: Optional[str] = "score"
    min_score: Optional[float] = 0
    max_results: Optional[int] = None
    include_confidence: Optional[bool] = True

# Global status
initialization_status = "not_started"

@app.get("/health")
async def health_check():
    """Basic health check"""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0-enhanced"
    }

@app.get("/data/status")
async def data_status():
    """Check data initialization status"""
    logger.info("Data status requested")
    return {
        "initialization_status": "completed",  # Simplified for testing
        "timestamp": datetime.now().isoformat(),
        "enhanced_features": True,
        "fallback_strategies": [
            "league_average_fallbacks",
            "team_based_estimates",
            "confidence_adjustments"
        ]
    }

@app.post("/analyze/pitcher-vs-team")
async def analyze_pitcher_vs_team(request: PredictionRequest):
    """
    Enhanced pitcher vs team analysis endpoint (simplified for testing)
    """
    logger.info(f"Enhanced analysis requested: {request.pitcher_name} vs {request.team}")
    
    # Return a mock response for testing
    return {
        "success": True,
        "pitcher_name": request.pitcher_name,
        "team": request.team.upper(),
        "predictions": [
            {
                "batter_name": "Test Player 1",
                "score": 75.5,
                "confidence": 0.85,
                "data_source": "pitcher_specific",
                "outcome_probabilities": {
                    "homerun": 8.5,
                    "hit": 25.2,
                    "reach_base": 32.1,
                    "strikeout": 22.3
                }
            },
            {
                "batter_name": "Test Player 2", 
                "score": 68.2,
                "confidence": 0.72,
                "data_source": "team_based",
                "outcome_probabilities": {
                    "homerun": 6.8,
                    "hit": 22.1,
                    "reach_base": 28.9,
                    "strikeout": 25.1
                }
            }
        ],
        "total_batters_analyzed": 2,
        "average_confidence": 0.785,
        "primary_data_source": "mixed",
        "reliability": "high"
    }

@app.get("/analyze/data-quality")
async def get_data_quality():
    """Data quality information"""
    logger.info("Data quality requested")
    return {
        "enhanced_features_active": True,
        "fallback_strategies": [
            "Real-time league averages by pitch type",
            "Team-based pitching profiles",
            "Position-based estimates",
            "Dynamic component weight adjustment"
        ],
        "analysis_statistics": {
            "total_analyses": 0,
            "success_rate": 100.0,
            "data_quality_breakdown": {
                "full_data_percentage": 80.0,
                "partial_data_percentage": 15.0,
                "team_based_percentage": 5.0,
                "league_average_percentage": 0.0
            }
        }
    }

@app.on_event("startup")
async def startup_event():
    """Startup event"""
    global initialization_status
    initialization_status = "completed"
    logger.info("🚀 Simplified Enhanced API started successfully!")
    logger.info("📡 Available at: http://localhost:8000")
    logger.info("📚 Docs at: http://localhost:8000/docs")

if __name__ == "__main__":
    print("🚀 Starting Simplified Enhanced Baseball Analysis API...")
    print("🔗 API will be available at: http://localhost:8000")
    print("📚 Documentation at: http://localhost:8000/docs")
    print("⚡ This is a simplified version for testing connectivity")
    
    uvicorn.run(
        "simple_enhanced_main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )