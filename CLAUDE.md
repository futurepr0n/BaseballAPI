# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the BaseballAPI repository.

## Development Commands

**Start the Enhanced API (Recommended):**
```bash
python enhanced_main.py
```
- Runs on localhost:8000 with missing data handling
- Auto-initializes from ../BaseballTracker/build/data
- Includes confidence scoring and fallback strategies

**Start the Original API:**
```bash
python main.py
```
- Runs on localhost:8000 (requires complete data)
- Full feature set without fallback support

**Download Latest Baseball Savant Data:**
```bash
python savant-scrape.py
```
- Downloads comprehensive batter and pitcher datasets
- Updates both BaseballTracker/public/data/stats/ and build/data/stats/
- Includes 200+ batter metrics and 300+ pitcher metrics

**Test API Endpoints:**
```bash
python test_enhanced_api.py
```
- Comprehensive endpoint testing
- Validates enhanced features and fallback scenarios

## Architecture Overview

### Enhanced Analysis Engine (Version 2.0)

The BaseballAPI provides sophisticated pitcher vs team matchup analysis with **enhanced missing data handling** and **confidence scoring**. The system uses a six-component weighted scoring algorithm with automatic fallbacks when data is incomplete.

**Core Features:**
- **Multi-factor Scoring**: 25+ variables combined into composite HR scores (0-100)
- **Arsenal-Specific Analysis**: Detailed pitch-by-pitch matchup evaluation (40% weight)
- **Contextual Intelligence**: Due factors, hot/cold streaks, exit velocity matchups (20% weight)
- **Missing Data Resilience**: Automatic fallbacks to league/team averages
- **Confidence Scoring**: Every prediction includes data quality assessment (0.0-1.0)
- **Real-time Integration**: Seamless BaseballTracker dashboard enhancement

### Six-Component Scoring System

1. **Arsenal Matchup** (40% weight) - Batter performance vs pitcher's specific pitch types
2. **Contextual Factors** (20% weight) - Due factors, hot/cold streaks, exit velocity
3. **Batter Overall Quality** (15% weight) - Player quality metrics with confidence adjustments
4. **Recent Daily Games** (10% weight) - Last N games performance trends
5. **Pitcher Overall Vulnerability** (10% weight) - Pitcher weakness analysis
6. **Historical Year-over-Year** (5% weight) - Performance changes over time

### Enhanced Data Handling

**Missing Data Fallback Strategy:**
```python
# Automatic fallback hierarchy
1. Individual player stats (if available)
2. Team-based aggregates (when individual missing)
3. League averages by position (starter vs reliever)
4. Overall league averages (final fallback)
```

**Confidence Adjustments:**
- **High Confidence** (1.0): Full individual data available (100+ PA)
- **Medium Confidence** (0.6-0.9): Partial data with team supplements
- **Low Confidence** (0.3-0.5): League averages with minimal individual data

## Core File Structure

### Main API Files
- **`enhanced_main.py`**: Enhanced FastAPI server with missing data handling
- **`main.py`**: Original FastAPI server (requires complete data)
- **`enhanced_analyzer.py`**: Enhanced analysis algorithms with fallback strategies
- **`analyzer.py`**: Original analysis algorithms
- **`enhanced_data_handler.py`**: High-level analysis coordination with missing data support

### Data Processing
- **`data_loader.py`**: Multi-year data initialization from CSV and JSON sources
- **`savant-scrape.py`**: Comprehensive Baseball Savant data downloader
- **`config.py`**: Scoring weights, thresholds, and configuration constants
- **`utils.py`**: Helper functions, normalization, and league average calculations

### Testing & Debugging
- **`test_enhanced_api.py`**: Comprehensive endpoint testing suite
- **`debug_main.py`**: Analysis processing and debugging functions
- **`diagnostic_main.py`**: System diagnostics and data quality assessment

## Data Sources & Integration

### Comprehensive Baseball Savant Integration

**New Custom Leaderboard Downloads (Added):**
- **`custom_batter_2025.csv`**: 200+ advanced batter metrics
  - Basic stats: Age, AB, PA, hits, HRs, strikeouts, walks
  - Rate stats: K%, BB%, AVG, SLG, OBP, OPS, ISO, BABIP
  - Statcast data: Exit velocity, launch angle, barrel rate, hard hit %
  - Advanced metrics: xBA, xSLG, wOBA, xwOBA, xOBP, xISO
  - Swing metrics: Attack angle, zone rates, whiff %, swing speed
  - Defensive metrics: Fielding stats, reaction times, outs above average

- **`custom_pitcher_2025.csv`**: 300+ advanced pitcher metrics
  - Basic stats: Games, IP, hits/HRs allowed, strikeouts, walks, ERA
  - Advanced metrics: xBA/xSLG/wOBA against, opponent contact rates
  - Pitch arsenal: Detailed breakdown by pitch type (FF, SL, CH, CU, SI, FC, etc.)
  - Pitch characteristics: Speed, spin rate, break measurements for each pitch
  - Zone control: In-zone vs out-zone metrics, edge %, meatball %
  - Situational stats: Inherited runners, quality starts, holds, saves

**Existing Data Sources:**
- **Arsenal Stats**: `hitterpitcharsenalstats_2025.csv`, `pitcherarsenalstats_2025.csv`
- **Exit Velocity**: `hitter_exit_velocity_2025.csv`, `pitcher_exit_velocity_2025.csv`
- **Batted Ball Data**: Comprehensive batted ball statistics by handedness matchups
- **Daily JSON**: Shared with BaseballTracker for recent performance tracking

### BaseballTracker Integration

**Shared Data Pipeline:**
- **JSON Files**: `../BaseballTracker/build/data/` for daily statistics
- **Prediction Enhancement**: BaseballAPI predictions enhanced with dashboard context
- **Real-time Updates**: Live integration with strategic intelligence dashboard
- **Badge System Integration**: API predictions automatically enhanced with 23-badge classification

## API Endpoints

### Enhanced Analysis Endpoints

**Primary Analysis:**
```bash
POST /analyze/pitcher-vs-team
{
  "pitcher_name": "MacKenzie Gore",
  "team": "SEA", 
  "include_confidence": true,
  "sort_by": "score",
  "max_results": 20
}
```

**Batch Analysis:**
```bash
POST /batch-analysis
{
  "matchups": [
    {"pitcher_name": "Pitcher 1", "team_abbr": "SEA"},
    {"pitcher_name": "Pitcher 2", "team_abbr": "NYY"}
  ],
  "sort_by": "hr",
  "limit": 50,
  "includeDashboardContext": true
}
```

**Data Quality Assessment:**
```bash
GET /analyze/data-quality
# Returns comprehensive data availability and confidence metrics
```

### Health & Diagnostics

**System Health:**
```bash
GET /health
# Returns API status and data initialization state
```

**Data Status:**
```bash
GET /data/status  
# Returns detailed data initialization status with enhancement info
```

**Data Reinitialization:**
```bash
POST /data/reinitialize
# Reloads all data sources (development use)
```

## Response Format

### Enhanced Prediction Object
```javascript
{
  "player_name": "Riley Greene",
  "team": "DET",
  "batter_hand": "L",
  "pitcher_hand": "R",
  
  // Core scores
  "hr_score": 83.92,                    // 0-100 composite score
  "hr_probability": 9.70,               // Percentage (2 decimal precision)
  "hit_probability": 22.05,             // Percentage
  "confidence": 0.85,                   // Data quality confidence (0.0-1.0)
  
  // Enhanced fields (added by BaseballTracker)
  "enhanced_confidence": 92.7,          // Base confidence + dashboard boost
  "enhanced_hr_score": 95.4,            // Base score + dashboard context
  "dashboard_context": {
    "badges": ["🔥 Hot Streak", "⚡ Due for HR"],
    "confidence_boost": 12,
    "standout_score": 95.4,
    "is_standout": true,
    "category": {
      "category": "high_confidence",
      "label": "High Confidence",
      "description": "Strong metrics with dashboard support"
    }
  },
  
  // Component breakdown
  "arsenal_matchup": 56.6,              // Arsenal analysis (0-100)
  "contextual": 72.8,                   // Due factors, streaks (0-100)
  "batter_overall": 78.3,               // Player quality (0-100)
  "recent_daily_games": 67.4,           // Recent form (0-100)
  "pitcher_overall": 45.2,              // Pitcher vulnerability (0-100)
  "historical_yoy_csv": 8.1,            // Historical trends (0-100)
  
  // Stadium & Weather Context (enhanced by BaseballTracker)
  "stadium_context": {
    "parkFactor": 1.12,
    "category": "Hitter Friendly",
    "isHitterFriendly": true
  },
  "weather_context": {
    "badge": "🌪️ Wind Boost", 
    "weatherImpact": "favorable"
  }
}
```

## Development Guidelines

### Enhanced Features Implementation

**Missing Data Handling:**
- Always implement fallback strategies for incomplete datasets
- Use confidence scoring to indicate data quality
- Blend individual stats with team/league averages based on sample size
- Provide meaningful analysis even with minimal data

**BaseballTracker Integration:**
- API responses automatically enhanced with dashboard context when requested
- Badge system integration provides 23 different performance indicators
- Stadium and weather context added through service layer integration
- Strategic intelligence features built on top of base API predictions

**Performance Optimization:**
- Cache frequently accessed data in memory
- Use singleton pattern for service instances
- Implement parallel processing for batch requests
- Optimize data loading with selective field parsing

### Data Quality Standards

**Confidence Thresholds:**
- **High**: 100+ PA for individual stats
- **Medium**: 50-99 PA with team supplementation  
- **Low**: <50 PA requiring heavy league average blending
- **Warning**: <30 PA triggers explicit low-confidence warnings

**Fallback Hierarchy:**
1. **Individual Player Stats** (preferred)
2. **Team Aggregates** (when individual missing)
3. **Position-Based League Averages** (starter vs reliever)
4. **Overall League Averages** (final fallback)

### Testing Strategy

**Endpoint Testing:**
```bash
python test_enhanced_api.py
# Tests all endpoints with various data scenarios
```

**Missing Data Scenarios:**
- Test with incomplete pitcher arsenal data
- Validate fallback to team/league averages
- Verify confidence scoring accuracy
- Check enhanced vs original endpoint parity

**Integration Testing:**
- Validate BaseballTracker dashboard enhancement
- Test badge system integration
- Verify stadium/weather context addition
- Check batch analysis with strategic intelligence

## Deployment Notes

**Production Considerations:**
- Enhanced version recommended for production use
- Requires BaseballTracker data directory structure
- Monitor confidence scores for data quality assessment
- Regular Baseball Savant data updates via savant-scrape.py

**Development Setup:**
- Clone alongside BaseballTracker repository
- Run savant-scrape.py for comprehensive data download
- Use enhanced_main.py for missing data resilience
- Test with various data completeness scenarios

**Performance Monitoring:**
- Monitor confidence score distributions
- Track fallback usage patterns
- Validate enhanced feature integration
- Monitor API response times for batch operations

The BaseballAPI serves as the analytical foundation for BaseballTracker's strategic intelligence system, providing sophisticated pitcher vs batter analysis with comprehensive fallback strategies and real-time dashboard integration.