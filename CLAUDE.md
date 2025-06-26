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

## Pitcher Vulnerability Analysis (Current Implementation)

### Core Vulnerability Calculation System

The BaseballAPI uses a sophisticated 6-component weighted scoring system implemented in `enhanced_analyzer.py` to assess pitcher vulnerability and batter matchup potential.

**Component Weight Distribution:**
- **Arsenal Matchup** (40%): Batter performance vs pitcher's specific pitch types
- **Contextual Factors** (20%): Due factors, hot/cold streaks, exit velocity matchups
- **Batter Overall Quality** (15%): Player quality metrics with confidence adjustments
- **Recent Daily Games** (10%): Last N games performance trends
- **Pitcher Overall Vulnerability** (10%): Pitcher weakness analysis across all batters
- **Historical Year-over-Year** (5%): Performance changes over time

**Enhanced Weight Factors (27 specific metrics):**
```python
ENHANCED_WEIGHTS = {
    'batter_vs_pitch_hr': 2.0,           # Highest weight - HR vs specific pitches
    'batter_overall_brl_percent': 2.5,    # Barrel rate importance
    'pitcher_vulnerability_hr': 1.8,      # Pitcher HR vulnerability
    'batter_vs_pitch_slg': 1.5,          # Slugging vs pitch types
    'recent_performance_bonus': 1.5,      # Recent form importance
    'batter_overall_iso': 1.5,           # Power metrics
    # ... 21 additional factors
}
```

**Fallback Weight Adjustment:**
When pitcher arsenal data is missing, component weights automatically adjust:
- Arsenal Matchup: 40% → 25% (reduced, using league averages)
- Batter Overall: 15% → 25% (increased to compensate)
- Pitcher Overall: 10% → 15% (increased)
- Recent Daily: 10% → 15% (increased)
- Historical: 5% → 10% (increased)
- Contextual: 20% (unchanged)

### League Average Fallback System

**Pitch Type Distribution (when pitcher data unavailable):**
```python
LEAGUE_AVERAGE_PITCH_DISTRIBUTION = {
    'FF': {'usage': 35.5, 'name': 'Four-Seam Fastball'},
    'SI': {'usage': 18.2, 'name': 'Sinker'},
    'SL': {'usage': 15.8, 'name': 'Slider'},
    'CH': {'usage': 12.1, 'name': 'Changeup'},
    'CU': {'usage': 8.7, 'name': 'Curveball'},
    # ... 3 additional pitch types
}
```

**Performance Metrics Per Pitch Type:**
- **BA/SLG/wOBA**: Contact quality against each pitch
- **Hard Hit %**: Hard contact rate (>95 mph exit velocity)
- **K%**: Strikeout rate for each pitch type
- **Run Value**: Expected run contribution per 100 pitches

**Real-time League Average Calculation:**
- Minimum 50+ PA threshold for individual data inclusion
- Automatic fallback hierarchy: Individual → Team → League → Defaults
- Confidence scoring (0.0-1.0) based on data completeness and sample size

### Current Methodology Limitations

**Missing Recent Form Analysis:**
- Season-long statistics treated with equal weight regardless of recency
- No consideration of pitcher's last 5 starts vs full season performance
- Recent struggles or improvements not factored into vulnerability assessment

**Absent Team Context Integration:**
- No analysis of opposing team's recent offensive surge/slump
- Missing consideration of key lineup changes or injury impacts
- Series momentum and head-to-head recent history not included

**Limited Situational Factors:**
- Home/away performance splits not weighted differently
- Ballpark HR factors available but not integrated into vulnerability calculation
- Weather impact (wind, temperature) not considered in pitcher assessment
- No pitcher fatigue indicators (rest days, recent pitch counts)

**Basic HR Rate Calculation:**
- Simple HR totals divided by games played
- No adjustment for quality of opposition faced
- Recent vs season-long HR trends not differentiated

### Enhancement Opportunities

**Identified Areas for Improvement:**
1. **Recent Performance Weighting**: Last 5 starts should carry 60% weight vs season 40%
2. **Team Offensive Context**: Integrate opponent's last 10 games scoring and power metrics
3. **Ballpark Integration**: Include stadium HR factors from existing stadiumContextService
4. **Pitcher Fatigue**: Add rest days, pitch count trends, and workload analysis
5. **Opposition Quality**: Adjust metrics based on strength of recent opponents faced

## Development Guidelines for Future Enhancements

### Critical Analysis Patterns to Maintain

**Avoid Infinite Positive Expectation Loops:**
- Always track failed attempts when analyzing bounce back or recovery patterns
- Implement rolling expectations that decrease with repeated failures
- Use historical pattern matching rather than treating each opportunity as independent
- Include confidence decay for extended negative streaks

**Enhanced Vulnerability Assessment:**
- Consider recent form (last 5 starts) more heavily than season-long averages
- Integrate opposing team's offensive trends and momentum
- Factor in contextual elements (ballpark, weather, rest, fatigue)
- Provide explanatory reasoning for vulnerability/dominance classifications

**Data Quality and Confidence Scoring:**
- Every prediction should include confidence assessment based on data completeness
- Implement graceful degradation when individual data is missing
- Use team/league averages as fallbacks with appropriate confidence adjustments
- Monitor and validate fallback usage patterns in production

### Future Integration Points

**BaseballTracker Integration:**
- Enhanced pitcher intelligence should feed into strategic recommendations
- Bounce back analysis requires failure tracking across multiple prediction cycles
- Team performance trends should influence individual player analysis
- Stadium and weather context services ready for integration

**Performance Monitoring:**
- Track confidence score distributions to validate prediction quality
- Monitor bounce back success rates vs predictions to calibrate penalty factors
- Validate that enhanced vulnerability calculations correlate with actual outcomes
- Regular assessment of fallback strategy effectiveness

The BaseballAPI serves as the analytical foundation for BaseballTracker's strategic intelligence system, providing sophisticated pitcher vs batter analysis with comprehensive fallback strategies and real-time dashboard integration.

## Critical Field Mapping Reference

### API Response → Frontend Field Mappings

**CRITICAL:** When adding new fields to API responses, they must match the exact field names expected by the PinheadsPlayhouse frontend. Mismatched field names will result in 0.0 values displayed in the UI.

#### Hitter Comprehensive Stats Field Mappings

| Frontend Column | Frontend Field Key | API Response Field | Status |
|----------------|--------------------|--------------------|--------|
| **AB Since HR** | `ab_since_last_hr` | `ab_since_last_hr` | ✅ Fixed |
| **Exp AB/HR** | `expected_ab_per_hr` | `expected_ab_per_hr` | ✅ Fixed |
| **H Since HR** | `h_since_last_hr` | `h_since_last_hr` | ✅ Fixed |
| **Exp H/HR** | `expected_h_per_hr` | `expected_h_per_hr` | ✅ Fixed |
| **Hitter SLG** | `hitter_slg` | `hitter_slg` | ✅ Working |
| **ISO 2024** | `iso_2024` | `iso_2024` | ✅ Fixed |
| **ISO 2025** | `iso_2025` | `iso_2025` | ✅ Fixed |

#### Pitcher Stats Field Mappings

| Frontend Column | Frontend Field Key | API Response Field | Status |
|----------------|--------------------|--------------------|--------|
| **Pitcher SLG** | `pitcher_slg` | `pitcher_slg` | ✅ Fixed |
| **P Home H Total** | `pitcher_home_h_total` | `pitcher_home_h_total` | ✅ Working |
| **P Home HR Total** | `pitcher_home_hr_total` | `pitcher_home_hr_total` | ✅ Working |
| **P Home K Total** | `pitcher_home_k_total` | `pitcher_home_k_total` | ✅ Working |

### Field Mapping Verification Process

**Before adding new fields to API responses:**

1. **Check Frontend Expectations:**
   ```bash
   grep -r "New Field Name" ../BaseballTracker/src/components/PinheadsPlayhouse/
   ```

2. **Verify Field Keys in PinheadsPlayhouse.js:**
   ```javascript
   // Look for this pattern in ../BaseballTracker/src/components/PinheadsPlayhouse/PinheadsPlayhouse.js
   { key: 'expected_field_name', label: 'Display Name' }
   ```

3. **Add to enhanced_analyzer.py with exact field name:**
   ```python
   # In enhanced_hr_score_with_missing_data_handling() return object
   'expected_field_name': calculated_value,  # Must match frontend key exactly
   ```

4. **Test API Response:**
   ```bash
   curl -X POST "http://localhost:8000/analyze/pitcher-vs-team" \
   -H "Content-Type: application/json" \
   -d '{"pitcher_name": "Test Pitcher", "team": "DET", "max_results": 1}' | \
   python -c "import json, sys; data=json.load(sys.stdin); print(data['predictions'][0]['expected_field_name'])"
   ```

### Common Field Mapping Mistakes

1. **Snake_case vs camelCase**: Frontend expects `snake_case` for field keys
2. **Partial name matching**: `h_since_hr` vs `h_since_last_hr` - they're different!
3. **Missing field calculations**: Field exists in frontend but not calculated in API
4. **Data type mismatches**: Frontend expects numbers, API returns strings or vice versa

### Name Matching System for Daily Data Lookups

#### Hitter Name Conversion Chain

**Daily JSON files use format: "A. Lastname" (e.g., "P. Alonso")**

```python
# In _calculate_comprehensive_hitter_stats():
if roster_full_name and ' ' in roster_full_name:
    name_parts = roster_full_name.split(' ')
    if len(name_parts) >= 2:
        initial_lastname_format = f"{name_parts[0][0]}. {name_parts[-1]}"  # "P. Alonso"

hitter_names_to_check = [
    batter_name.lower(),                    # API request name
    roster_short_name.lower(),              # "p. alonso" from roster
    roster_full_name.lower(),               # "pete alonso" from roster  
    csv_format_name.lower(),                # "alonso, pete" (CSV format)
    initial_lastname_format.lower(),        # "p. alonso" (daily JSON format) - CRITICAL
]
```

#### Pitcher Name Conversion Chain

**Same pattern applies to pitcher lookups in daily data for trend analysis and home game stats.**

### Data Source Hierarchy

1. **Roster Data**: `fullName` field used for API requests
2. **Daily JSON**: `name` field in "A. Lastname" format for game-by-game stats
3. **CSV Import**: "Lastname, Firstname" format from external sources

### Development Debugging

**When hitter stats show 0.0 values:**

1. Check field name mapping first (most common issue)
2. Verify hitter name matching in logs: `🏏 HITTER STATS: [Name] - [stats]`
3. Confirm comprehensive stats calculation: `🔍 HITTER NAME MATCH: [results]`
4. Test individual field calculations in isolation

**Server restart required after field mapping changes:**
```bash
# Kill existing server
ps aux | grep enhanced_main | grep -v grep | awk '{print $2}' | xargs kill

# Restart with venv
source venv/bin/activate && python enhanced_main.py --port 8000 &
```