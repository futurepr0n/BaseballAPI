# BaseballAPI Analysis System Documentation

## Overview

The BaseballAPI is a sophisticated **FastAPI-based analysis engine** that provides advanced pitcher vs team matchup analysis for baseball home run and hitting predictions. It uses a multi-factor scoring system with 25+ variables to analyze individual batter performance against specific pitchers.

## Core Architecture

### Six-Component Weighted Scoring System

The system calculates a final HR score (0-100) using six weighted components:

1. **Arsenal Matchup** (40% weight) - Batter vs pitcher's specific pitch types
2. **Contextual Factors** (20% weight) - Due factors, hot/cold streaks  
3. **Batter Overall Quality** (15% weight) - Player quality metrics
4. **Recent Daily Games** (10% weight) - Last N games performance trends
5. **Pitcher Overall Vulnerability** (10% weight) - Pitcher weakness analysis
6. **Historical Year-over-Year Trends** (5% weight) - Performance changes

### Final Score Calculation
```python
final_hr_score = (
    arsenal_matchup_score * 0.40 +
    contextual_factors_score * 0.20 +
    batter_overall_score * 0.15 +
    recent_daily_games_score * 0.10 +
    pitcher_overall_score * 0.10 +
    historical_yoy_score * 0.05
)
```

## Detailed Component Analysis

### 1. Arsenal Matchup Analysis (40% - Most Critical)

**Purpose**: Analyzes how well a batter performs against each specific pitch type in the pitcher's arsenal.

**Process**:
1. **Pitch Type Breakdown**: Analyzes Fastball, Slider, Changeup, Curveball, etc.
2. **Batter Performance**: SLG, HR rate, Hard Hit% vs each pitch type
3. **Pitcher Vulnerability**: SLG allowed, HR allowed, Run Value with each pitch
4. **Usage Weighting**: Heavily weights pitches the pitcher throws frequently
5. **Handedness Splits**: Accounts for L vs R, R vs R, etc. matchups

**Example Calculation**:
```python
# For each pitch type:
batter_slg_vs_fastball = 0.650    # Normalized to 75/100
pitcher_slg_allowed_fastball = 0.520  # Normalized to 65/100
fastball_usage_percent = 0.45     # 45% of pitcher's arsenal

component_score = (
    (batter_normalized * 0.6 + pitcher_normalized * 0.4) * usage_percent
)
# Result: (75 * 0.6 + 65 * 0.4) * 0.45 = 30.6
```

**Key Factors**:
- **Weighted by usage**: Fastballs thrown 60% get more weight than Sliders thrown 15%
- **Multiple metrics**: SLG, HR rate, Hard Hit%, K%, Run Value
- **Switch hitter logic**: Automatically selects optimal handedness vs pitcher

### 2. Contextual Factors (20% - Timing Sensitive)

**Due for HR Analysis**:
- **AB-based calculation**: Games since last HR vs expected frequency based on career rate
- **Hits-based calculation**: Hits since last HR vs expected ratio (~1 HR per 10 hits)
- **Raw scoring**: Players "overdue" receive bonuses, recent HR hitters get penalties

**Hot/Cold Streak Detection**:
```python
# Heating Up: High contact rate but no recent HRs
if recent_contact_rate > league_avg and recent_hrs == 0:
    heating_up_bonus = normalize_calculated(contact_advantage)

# Cold Batter: Very low recent contact rate  
if recent_contact_rate < (league_avg * 0.7):
    cold_batter_penalty = normalize_calculated(contact_deficit)
```

**Exit Velocity Matchups**:
- Compares batter's average exit velocity vs pitcher's exit velocity allowed
- Normalized against league percentiles
- Bonus for favorable matchups

**Requirements**: Minimum 20 PA in recent games for trend evaluation

### 3. Probability Calculations

Four outcome probabilities are calculated based on the composite HR score:

```python
base_prob_factor = final_hr_score / 100

# With caps, floors, and PA adjustments:
hr_probability = min(40, max(0.5, base_prob_factor * 10 + batter_pa_2025 * 0.005))
hit_probability = min(60, max(5, base_prob_factor * 20 + batter_pa_2025 * 0.02))
reach_base_probability = min(70, max(8, base_prob_factor * 25 + batter_pa_2025 * 0.03))
strikeout_probability = max(10, min(80, 70 - base_prob_factor * 15 + batter_pa_2025 * 0.01))
```

**Probability Features**:
- **Sample size adjustments**: More PA = more confidence = higher probabilities
- **Realistic caps**: HR probability capped at 40%, Hit at 60%
- **Floor protection**: Minimum probabilities prevent unrealistic zeros
- **Inverse correlation**: Higher HR scores = lower strikeout probability

### 4. Recent Performance Integration (10%)

**Trend Analysis**:
```python
# Split recent games into two halves
recent_half_hr_rate = recent_games[:mid_point].hr_per_pa
earlier_half_hr_rate = recent_games[mid_point:].hr_per_pa

trend_direction = "improving" if recent_half_hr_rate > earlier_half_hr_rate else "declining"
trend_magnitude = abs(recent_half_hr_rate - earlier_half_hr_rate)
```

**Performance Metrics**:
- **Aggregated stats**: Recent AVG, OBP, SLG across last N games
- **Rate calculations**: HR rate, K rate, BB rate
- **Trend detection**: First half vs second half performance comparison
- **Recency weighting**: More recent games weighted higher

### 5. Batter Overall Quality (15%)

**Key Metrics**:
- **Barrel Percentage**: Hardest hit balls (optimal launch angle + exit velocity)
- **Hard Hit Percentage**: Exit velocity > 95 mph
- **ISO (Isolated Power)**: SLG - AVG, measures extra-base hit ability
- **Exit Velocity**: Average and top percentiles

**Confidence Adjustments**:
```python
def adjust_stat_with_confidence(stat_value, pa_count, metric_type, league_avg):
    confidence_factor = min(1.0, pa_count / K_CONFIDENCE_PA)  # 100 PA for full confidence
    adjusted_value = stat_value * confidence_factor + league_avg * (1 - confidence_factor)
    return adjusted_value
```

### 6. Advanced Normalization System

**Metric Ranges**: System calculates league-wide percentiles for all metrics:
```python
def normalize_calculated(value, metric_type, metric_ranges, higher_is_better=True):
    # Returns 0-100 score based on league percentiles
    percentile = calculate_percentile_rank(value, metric_ranges[metric_type])
    return percentile if higher_is_better else (100 - percentile)
```

**Sample Size Handling**:
- **30 PA minimum**: Below this, heavy league average blending
- **50 PA threshold**: Warning displayed for low confidence
- **100 PA optimal**: Full confidence in individual statistics

## API Response Structure

### Prediction Object
```javascript
{
  "player_name": "Riley Greene",
  "player_id": "663656",
  "team": "DET",
  "batter_hand": "L",
  "pitcher_hand": "R",
  
  // Core scores
  "hr_score": 83.92,                    // 0-100 composite score
  "hr_probability": 9.7,                // Percentage (already converted)
  "hit_probability": 22.0,              // Percentage  
  "reach_base_probability": 28.5,       // Percentage
  "strikeout_probability": 24.1,        // Percentage
  
  // Recent performance
  "recent_avg": 0.298,
  "hr_rate": 0.045,
  "obp": 0.365,
  
  // Contextual factors
  "ab_due": 5.9,                        // AB since last HR vs expected
  "hits_due": 2.3,                      // Hits since last HR vs expected
  "heating_up": 12.5,                   // Contact trend bonus
  "cold": 0.0,                          // Cold streak penalty
  
  // Component breakdown
  "arsenal_matchup": 56.6,              // Arsenal component (0-100)
  "batter_overall": 78.3,               // Batter quality (0-100)
  "pitcher_overall": 45.2,              // Pitcher vulnerability (0-100)
  "historical_yoy_csv": 8.1,            // Historical trends (0-100)
  "recent_daily_games": 67.4,           // Recent performance (0-100)
  "contextual": 72.8,                   // Contextual factors (0-100)
  
  // Arsenal-specific
  "hitter_slg": 0.587,                  // Weighted SLG vs pitcher's arsenal
  "pitcher_slg": 0.443,                 // Weighted SLG allowed with arsenal
  
  // Additional details
  "ab_since_last_hr": 23,
  "expected_ab_per_hr": 18.5,
  "contact_trend": "improving",
  "iso_2024": 0.185,
  "iso_2025": 0.203,
  "ev_matchup_score": 65.2
}
```

## Sorting and Filtering Options

### Available Sort Fields
- **score**: Overall HR Score (default)
- **hr/homerun**: HR Probability  
- **hit**: Hit Probability
- **reach_base**: Reach Base Probability
- **strikeout**: Strikeout Probability (ascending)
- **arsenal_matchup**: Arsenal component score
- **recent_avg**: Recent batting average
- **ab_due**: Due for HR (AB-based)
- **heating_up**: Hot streak indicator

### Filter Capabilities
```javascript
// Example filter criteria
{
  "min_score": 70,                      // Minimum HR score
  "min_hr_prob": 8.0,                   // Minimum HR probability  
  "max_k_prob": 25.0,                   // Maximum strikeout probability
  "contact_trend": "improving",          // Only improving hitters
  "min_due_ab": 10                      // Only players overdue for HR
}
```

## Technical Implementation

### Key Files
- **`main.py`**: FastAPI server with endpoints
- **`enhanced_main.py`**: Enhanced FastAPI server with missing data handling
- **`analyzer.py`**: Core scoring algorithms  
- **`enhanced_analyzer.py`**: Enhanced algorithms with fallback strategies
- **`enhanced_data_handler.py`**: High-level analysis coordination with missing data support
- **`data_loader.py`**: Multi-year data initialization
- **`config.py`**: Weights, thresholds, and constants
- **`utils.py`**: Helper functions and normalization
- **`debug_main.py`**: Analysis processing functions

### Enhanced Features (Version 2.0)
- **Missing Data Fallbacks**: Automatic fallback to league averages when pitcher data unavailable
- **Confidence Scoring**: Every prediction includes confidence level (0.0-1.0)
- **Dynamic Weight Adjustment**: Component weights adjust based on data availability
- **Team-Based Estimates**: Use team pitching profiles when individual data missing
- **Position-Based Profiles**: Different baselines for starters vs relievers
- **Real-time League Averages**: Calculate league averages from available data

### Data Sources
- **Historical CSV**: `mlb_stats/` directory with pitch arsenal data
- **Daily JSON**: Shared with BaseballTracker for recent performance
- **Roster Data**: Player info and handedness
- **League Averages**: Calculated from full dataset

### Performance Features
- **Startup initialization**: Loads all data into memory
- **Caching**: Results cached for repeat requests  
- **Batch processing**: Multiple matchups in single request
- **Error handling**: Graceful degradation when data missing

## Development and Debugging

### Starting the API

**Enhanced Version (Recommended):**
```bash
cd BaseballAPI
python enhanced_main.py
# Runs on localhost:8000 with enhanced missing data handling
# Auto-initializes data from ../BaseballTracker/build/data
```

**Original Version:**
```bash
cd BaseballAPI
python main.py
# Runs on localhost:8000
# Auto-initializes data from ../BaseballTracker/build/data
```

### Health Checks
```bash
GET /health                    # Check API status
GET /data/status              # Check data initialization with enhancement info
POST /data/reinitialize       # Reload data (development)
GET /analyze/data-quality     # Enhanced: Data quality assessment
```

### Enhanced Endpoints
```bash
# Enhanced pitcher vs team analysis
POST /analyze/pitcher-vs-team
{
  "pitcher_name": "MacKenzie Gore",
  "team": "SEA",
  "include_confidence": true
}

# Bulk analysis with missing data handling
POST /analyze/bulk-predictions
{
  "matchups": [
    {"pitcher": "Pitcher Name", "team": "SEA"},
    {"pitcher": "Another Pitcher", "team": "NYY"}
  ]
}

# Generate comprehensive report
POST /analyze/generate-report
{
  "pitcher_name": "MacKenzie Gore",
  "team": "SEA"
}
```

### Common Issues & Solutions

**Enhanced System:**
- **Missing pitcher data**: ✅ Automatically handled with fallbacks
- **Data path errors**: Ensure `../BaseballTracker/build/data` exists
- **Missing CSV files**: ✅ Team and league averages used as fallbacks
- **Low PA warnings**: ✅ Confidence adjustments applied automatically
- **Partial arsenal data**: ✅ Blended with league averages

**Original System:**
- **Data path errors**: Ensure `../BaseballTracker/build/data` exists
- **Missing CSV files**: Check `mlb_stats/` directory
- **Low PA warnings**: Players with <50 PA get confidence adjustments
- **Missing arsenal data**: ❌ Analysis fails completely

### Debug Output
The system provides extensive logging:
```python
DEBUG: Enhanced process_pitcher_vs_team(MacKenzie Gore, SEA)
DEBUG: Pitcher ID found: 665563
DEBUG: Found 12 batters for team SEA
DEBUG: Player analysis complete - Final scores calculated
```

## Algorithm Philosophy

This system represents a **sophisticated, multi-layered approach** to baseball analysis that:

1. **Prioritizes matchup specifics** (40% arsenal weight) over general stats
2. **Incorporates timing and context** (20% contextual weight) for real-world factors  
3. **Balances multiple data sources** (historical, recent, overall quality)
4. **Handles uncertainty gracefully** (confidence adjustments, league average blending)
5. **Provides actionable probabilities** (realistic caps and floors)

The result is a system that goes far beyond simple batting averages to analyze the **micro-level dynamics** of how specific batters perform against specific pitchers based on pitch-by-pitch matchups, recent form, and contextual timing factors.