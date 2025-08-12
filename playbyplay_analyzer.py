"""
Play-by-Play Analyzer for Pitcher Vulnerability Analysis
Processes historical play-by-play data to identify pitcher weaknesses and patterns
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PlayByPlayAnalyzer:
    def __init__(self, data_path: str = "../BaseballData/data/play-by-play"):
        """Initialize the play-by-play analyzer with data path"""
        self.data_path = Path(data_path)
        self.vulnerability_cache = {}
        self.pattern_cache = {}
        
    def analyze_pitcher_vulnerabilities(self, pitcher_name: str, limit_games: int = 50) -> Dict[str, Any]:
        """
        Analyze a pitcher's vulnerabilities from recent play-by-play data
        
        Returns comprehensive vulnerability analysis including:
        - Pitch type vulnerabilities
        - Inning-specific patterns
        - Count-specific weaknesses
        - Batter position vulnerabilities
        """
        pitcher_games = self._find_pitcher_games(pitcher_name, limit_games)
        
        if not pitcher_games:
            logger.warning(f"No games found for pitcher: {pitcher_name}")
            return self._empty_analysis()
        
        analysis = {
            "pitcher_name": pitcher_name,
            "games_analyzed": len(pitcher_games),
            "pitch_vulnerabilities": self._analyze_pitch_vulnerabilities(pitcher_games, pitcher_name),
            "inning_patterns": self._analyze_inning_patterns(pitcher_games, pitcher_name),
            "count_weaknesses": self._analyze_count_weaknesses(pitcher_games, pitcher_name),
            "position_vulnerabilities": self._analyze_position_vulnerabilities(pitcher_games, pitcher_name),
            "pattern_recognition": self._analyze_pitch_patterns(pitcher_games, pitcher_name),
            "timing_windows": self._analyze_timing_windows(pitcher_games, pitcher_name),
            "recent_form": self._analyze_recent_form(pitcher_games, pitcher_name)
        }
        
        # Calculate overall vulnerability score
        analysis["overall_vulnerability_score"] = self._calculate_overall_vulnerability(analysis)
        
        return analysis
    
    def _find_pitcher_games(self, pitcher_name: str, limit: int) -> List[Dict]:
        """Find recent games where the pitcher appeared"""
        pitcher_games = []
        
        # Get all play-by-play files sorted by date (most recent first)
        pbp_files = sorted(self.data_path.glob("*.json"), reverse=True)
        
        for file_path in pbp_files:
            if len(pitcher_games) >= limit:
                break
                
            try:
                with open(file_path, 'r') as f:
                    game_data = json.load(f)
                    
                # Check if pitcher appears in this game
                if self._pitcher_in_game(pitcher_name, game_data):
                    pitcher_games.append(game_data)
                    
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
                continue
        
        return pitcher_games
    
    def _pitcher_in_game(self, pitcher_name: str, game_data: Dict) -> bool:
        """Check if a pitcher appears in the game with enhanced name matching"""
        plays = game_data.get("plays", [])
        
        # Normalize the search name
        search_name = pitcher_name.lower().strip()
        
        for play in plays:
            play_pitcher = play.get("pitcher", "").lower().strip()
            if not play_pitcher:
                continue
                
            # Exact match
            if play_pitcher == search_name:
                return True
                
            # Last name match (e.g., "Strider" matches "Spencer Strider")
            search_parts = search_name.split()
            play_parts = play_pitcher.split()
            
            if len(search_parts) > 0 and len(play_parts) > 0:
                # Check if search is just last name and matches play pitcher's last name
                if len(search_parts) == 1 and search_parts[0] == play_parts[-1]:
                    return True
                    
                # Check if search is "Last, First" format
                if ", " in search_name:
                    last, first = search_name.split(", ", 1)
                    if f"{first} {last}" == play_pitcher:
                        return True
                        
                # Check partial name matching (both first and last name)
                if len(search_parts) >= 2 and len(play_parts) >= 2:
                    # Check if first initial + last name matches
                    if (search_parts[0][0] == play_parts[0][0] and 
                        search_parts[-1] == play_parts[-1]):
                        return True
                        
        return False
        
    def _pitcher_name_matches(self, search_name: str, play_pitcher: str) -> bool:
        """Enhanced pitcher name matching utility"""
        if not search_name or not play_pitcher:
            return False
            
        search_name = search_name.lower().strip()
        play_pitcher = play_pitcher.lower().strip()
        
        # Exact match
        if search_name == play_pitcher:
            return True
            
        # Split into parts for more sophisticated matching
        search_parts = search_name.split()
        play_parts = play_pitcher.split()
        
        if len(search_parts) == 0 or len(play_parts) == 0:
            return False
            
        # Single name matching (likely last name)
        if len(search_parts) == 1:
            # Check if search matches any part of play pitcher name
            return search_parts[0] in play_parts
            
        # Multiple parts - check for various formats
        if len(search_parts) >= 2 and len(play_parts) >= 2:
            # "First Last" vs "First Last"
            if search_parts[0] == play_parts[0] and search_parts[-1] == play_parts[-1]:
                return True
                
            # "F. Last" vs "First Last" 
            if (len(search_parts[0]) == 2 and search_parts[0].endswith('.') and 
                search_parts[0][0] == play_parts[0][0] and 
                search_parts[-1] == play_parts[-1]):
                return True
                
        # "Last, First" format
        if ", " in search_name:
            try:
                last, first = search_name.split(", ", 1)
                return f"{first} {last}" == play_pitcher
            except:
                pass
                
        return False
    
    def _analyze_pitch_vulnerabilities(self, games: List[Dict], pitcher_name: str) -> Dict:
        """Analyze which pitch types are most vulnerable with enhanced matching"""
        pitch_outcomes = defaultdict(lambda: {"total": 0, "hits": 0, "hrs": 0, "strikeouts": 0})
        total_pitches_analyzed = 0
        
        for game in games:
            for play in game.get("plays", []):
                # Use enhanced pitcher matching
                if not self._pitcher_name_matches(pitcher_name, play.get("pitcher", "")):
                    continue
                    
                result = play.get("play_result", "").lower()
                pitch_sequence = play.get("pitch_sequence", [])
                
                for pitch in pitch_sequence:
                    pitch_type = pitch.get("pitch_type", "Unknown")
                    if pitch_type == "Unknown":
                        continue
                        
                    pitch_outcomes[pitch_type]["total"] += 1
                    total_pitches_analyzed += 1
                    
                    # Improved result detection
                    if any(hr_term in result for hr_term in ["home run", "homer", "hr"]):
                        pitch_outcomes[pitch_type]["hrs"] += 1
                    elif any(hit_term in result for hit_term in ["single", "double", "triple", "hit", "line drive", "ground ball hit"]):
                        pitch_outcomes[pitch_type]["hits"] += 1
                    elif any(k_term in result for k_term in ["strikeout", "struck out", "swinging strike", "called strike"]) or pitch.get("result", "").lower() in ["strike swinging", "strike looking"]:
                        pitch_outcomes[pitch_type]["strikeouts"] += 1
        
        # Calculate vulnerability scores with improved analysis
        vulnerabilities = {}
        for pitch_type, outcomes in pitch_outcomes.items():
            if outcomes["total"] >= 3:  # Require minimum sample size
                hr_rate = outcomes["hrs"] / outcomes["total"]
                hit_rate = outcomes["hits"] / outcomes["total"]
                k_rate = outcomes["strikeouts"] / outcomes["total"]
                
                # Enhanced vulnerability scoring
                # Home runs are weighted more heavily, strikeouts reduce vulnerability
                vulnerability_score = (hr_rate * 120) + (hit_rate * 60) - (k_rate * 40)
                
                # Adjust for small sample sizes
                sample_adjustment = min(1.0, outcomes["total"] / 20)  # Full confidence at 20+ pitches
                adjusted_score = vulnerability_score * sample_adjustment
                
                vulnerabilities[pitch_type] = {
                    "vulnerability_score": max(0, adjusted_score),
                    "hr_rate": hr_rate,
                    "hit_rate": hit_rate,
                    "strikeout_rate": k_rate,
                    "sample_size": outcomes["total"],
                    "confidence": sample_adjustment
                }
        
        logger.info(f"🎯 PITCH ANALYSIS: Analyzed {total_pitches_analyzed} total pitches for {pitcher_name} across {len(games)} games")
        
        return vulnerabilities
    
    def _analyze_inning_patterns(self, games: List[Dict], pitcher_name: str) -> Dict:
        """Analyze performance patterns by inning with enhanced matching"""
        inning_outcomes = defaultdict(lambda: {"total": 0, "hits": 0, "hrs": 0, "walks": 0})
        
        for game in games:
            for play in game.get("plays", []):
                if not self._pitcher_name_matches(pitcher_name, play.get("pitcher", "")):
                    continue
                    
                inning = play.get("inning", 0)
                result = play.get("play_result", "").lower()
                
                inning_outcomes[inning]["total"] += 1
                
                if any(hr_term in result for hr_term in ["home run", "homer", "hr"]):
                    inning_outcomes[inning]["hrs"] += 1
                if any(hit_term in result for hit_term in ["single", "double", "triple", "hit", "home run", "line drive", "ground ball hit"]):
                    inning_outcomes[inning]["hits"] += 1
                if any(walk_term in result for walk_term in ["walk", "walked", "base on balls", "bb"]):
                    inning_outcomes[inning]["walks"] += 1
        
        # Calculate vulnerability by inning
        patterns = {}
        for inning, outcomes in inning_outcomes.items():
            if outcomes["total"] > 0:
                vulnerability_score = (
                    (outcomes["hrs"] / outcomes["total"]) * 100 +
                    (outcomes["hits"] / outcomes["total"]) * 50 +
                    (outcomes["walks"] / outcomes["total"]) * 25
                )
                
                patterns[f"inning_{inning}"] = {
                    "vulnerability_score": vulnerability_score,
                    "hr_frequency": outcomes["hrs"] / outcomes["total"],
                    "hit_frequency": outcomes["hits"] / outcomes["total"],
                    "walk_frequency": outcomes["walks"] / outcomes["total"],
                    "sample_size": outcomes["total"]
                }
        
        return patterns
    
    def _analyze_count_weaknesses(self, games: List[Dict], pitcher_name: str) -> Dict:
        """Analyze performance in different count situations with enhanced matching"""
        count_outcomes = defaultdict(lambda: {"total": 0, "favorable": 0, "unfavorable": 0})
        
        for game in games:
            for play in game.get("plays", []):
                if not self._pitcher_name_matches(pitcher_name, play.get("pitcher", "")):
                    continue
                    
                for pitch in play.get("pitch_sequence", []):
                    balls = pitch.get("balls", 0)
                    strikes = pitch.get("strikes", 0)
                    count = f"{balls}-{strikes}"
                    result = pitch.get("result", "").lower()
                    
                    count_outcomes[count]["total"] += 1
                    
                    if any(good in result for good in ["strike", "foul"]):
                        count_outcomes[count]["favorable"] += 1
                    elif any(bad in result for bad in ["ball", "hit", "home run"]):
                        count_outcomes[count]["unfavorable"] += 1
        
        # Calculate count-specific weaknesses
        weaknesses = {}
        for count, outcomes in count_outcomes.items():
            if outcomes["total"] > 0:
                weakness_score = (outcomes["unfavorable"] / outcomes["total"]) * 100
                
                weaknesses[count] = {
                    "weakness_score": weakness_score,
                    "control_rate": outcomes["favorable"] / outcomes["total"],
                    "sample_size": outcomes["total"]
                }
        
        return weaknesses
    
    def _analyze_position_vulnerabilities(self, games: List[Dict], pitcher_name: str) -> Dict:
        """Analyze vulnerabilities by individual batting order position (1-9)"""
        position_outcomes = defaultdict(lambda: {"total": 0, "hits": 0, "hrs": 0})
        total_plays_analyzed = 0
        games_with_data = 0
        
        # Track batting order by inferring from play sequence within innings
        for game in games:
            # Group plays by inning to track batting order
            inning_batters = defaultdict(list)
            
            for play in game.get("plays", []):
                if not self._pitcher_name_matches(pitcher_name, play.get("pitcher", "")):
                    continue
                    
                inning = play.get("inning", 0)
                half = play.get("inning_half", "").lower()
                batter = play.get("batter", "")
                
                if batter and inning > 0:
                    # Create unique key for inning and half
                    inning_key = f"{inning}_{half}"
                    if batter not in [b["name"] for b in inning_batters[inning_key]]:
                        inning_batters[inning_key].append({
                            "name": batter,
                            "play": play
                        })
            
            # Analyze each inning's batting order
            for inning_key, batters in inning_batters.items():
                if not batters:
                    continue
                    
                # Determine starting position based on inning and previous innings
                base_position = self._estimate_lineup_position(inning_key, batters, inning_batters)
                
                for i, batter_info in enumerate(batters):
                    # Calculate batting position (1-9, cycling)
                    position = ((base_position + i - 1) % 9) + 1
                    play = batter_info["play"]
                    result = play.get("play_result", "").lower()
                    
                    # Track individual positions (1-9)
                    pos_key = f"position_{position}"
                    
                    position_outcomes[pos_key]["total"] += 1
                    
                    # Track hits and home runs
                    if any(hr_term in result for hr_term in ["home run", "homer", "hr"]):
                        position_outcomes[pos_key]["hrs"] += 1
                        position_outcomes[pos_key]["hits"] += 1  # HR counts as hit too
                    elif any(hit_term in result for hit_term in ["single", "double", "triple", "hit", "line drive", "ground ball hit"]):
                        position_outcomes[pos_key]["hits"] += 1
                    
                    total_plays_analyzed += 1
                        
            if inning_batters:
                games_with_data += 1
        
        # Calculate vulnerability scores for all 9 positions
        logger.info(f"🎯 POSITION ANALYSIS: Analyzed {total_plays_analyzed} total plays for {pitcher_name} across {games_with_data} games with batting data")
        vulnerabilities = {}
        
        # Debug: Log raw position outcomes
        logger.info(f"🎯 POSITION DEBUG - RAW OUTCOMES for {pitcher_name}: {dict(position_outcomes)}")
        
        # Ensure all 9 positions are represented in the response
        for position in range(1, 10):
            pos_key = f"position_{position}"
            outcomes = position_outcomes[pos_key]
            
            if outcomes["total"] > 0:
                hr_rate = outcomes["hrs"] / outcomes["total"]
                hit_rate = outcomes["hits"] / outcomes["total"]
                
                # Enhanced vulnerability scoring
                # Home runs weighted more heavily than regular hits
                vulnerability_score = (hr_rate * 80) + (hit_rate * 40)
                
                # Sample size adjustment - more lenient for individual positions
                sample_adjustment = min(1.0, outcomes["total"] / 8)  # Full confidence at 8+ at-bats per position
                adjusted_score = vulnerability_score * sample_adjustment
                
                vulnerabilities[pos_key] = {
                    "vulnerability_score": round(adjusted_score, 1),
                    "hr_rate": round(hr_rate, 3),
                    "hit_rate": round(hit_rate, 3),
                    "sample_size": outcomes["total"]
                }
            else:
                # Provide zero values for positions with no data
                vulnerabilities[pos_key] = {
                    "vulnerability_score": 0.0,
                    "hr_rate": 0.000,
                    "hit_rate": 0.000,
                    "sample_size": 0
                }
        
        # Debug: Log final vulnerabilities object
        logger.info(f"🎯 POSITION DEBUG - FINAL VULNERABILITIES for {pitcher_name}: {vulnerabilities}")
        
        return vulnerabilities
    
    def _estimate_lineup_position(self, inning_key: str, batters: List[Dict], all_innings: Dict) -> int:
        """Estimate the starting batting position for an inning based on context"""
        # Parse inning info
        parts = inning_key.split("_")
        inning_num = int(parts[0])
        half = parts[1]
        
        # For first inning, position starts at 1
        if inning_num == 1:
            return 1
            
        # For subsequent innings, try to track where we left off
        # This is a simplified approach - look at previous half inning
        prev_batters_count = 0
        
        # Count total batters from all previous half innings
        for prev_inning_key, prev_batters in all_innings.items():
            prev_parts = prev_inning_key.split("_")
            prev_inning_num = int(prev_parts[0])
            prev_half = prev_parts[1]
            
            # Only count if it's before current inning or same inning but different half
            if (prev_inning_num < inning_num or 
                (prev_inning_num == inning_num and prev_half != half and prev_half == "top")):
                prev_batters_count += len(prev_batters)
        
        # Estimate starting position (cycling through 1-9)
        estimated_position = (prev_batters_count % 9) + 1
        return estimated_position
    
    def _analyze_pitch_patterns(self, games: List[Dict], pitcher_name: str) -> Dict:
        """Analyze predictable pitch sequences with enhanced matching"""
        sequences = defaultdict(int)
        sequence_outcomes = defaultdict(lambda: {"total": 0, "successful": 0})
        
        for game in games:
            for play in game.get("plays", []):
                if not self._pitcher_name_matches(pitcher_name, play.get("pitcher", "")):
                    continue
                    
                pitch_sequence = play.get("pitch_sequence", [])
                if len(pitch_sequence) >= 2:
                    for i in range(len(pitch_sequence) - 1):
                        seq = f"{pitch_sequence[i].get('pitch_type', 'Unknown')} -> {pitch_sequence[i+1].get('pitch_type', 'Unknown')}"
                        sequences[seq] += 1
                        
                        # Track if sequence was successful (resulted in strike/out)
                        result = pitch_sequence[i+1].get("result", "").lower()
                        sequence_outcomes[seq]["total"] += 1
                        if any(good in result for good in ["strike", "foul", "out"]):
                            sequence_outcomes[seq]["successful"] += 1
        
        # Calculate predictability score
        total_sequences = sum(sequences.values())
        predictability_score = 0
        top_sequences = []
        
        if total_sequences > 0:
            # High frequency sequences indicate predictability
            for seq, count in sorted(sequences.items(), key=lambda x: x[1], reverse=True)[:5]:
                frequency = count / total_sequences
                success_rate = sequence_outcomes[seq]["successful"] / sequence_outcomes[seq]["total"] if sequence_outcomes[seq]["total"] > 0 else 0
                
                # More predictable if high frequency but low success rate
                predictability_contribution = frequency * (1 - success_rate) * 100
                predictability_score += predictability_contribution
                
                top_sequences.append({
                    "sequence": seq,
                    "frequency": frequency,
                    "success_rate": success_rate,
                    "count": count
                })
        
        return {
            "predictability_score": min(100, predictability_score * 10),  # Scale to 0-100
            "top_sequences": top_sequences,
            "total_sequences_analyzed": total_sequences
        }
    
    def _analyze_timing_windows(self, games: List[Dict], pitcher_name: str) -> Dict:
        """Analyze performance degradation over pitch count with enhanced matching"""
        pitch_count_outcomes = defaultdict(lambda: {"total": 0, "hits": 0, "velocity_sum": 0})
        
        for game in games:
            game_pitch_count = 0
            for play in game.get("plays", []):
                if not self._pitcher_name_matches(pitcher_name, play.get("pitcher", "")):
                    continue
                    
                for pitch in play.get("pitch_sequence", []):
                    game_pitch_count += 1
                    pitch_range = f"{((game_pitch_count - 1) // 20) * 20 + 1}-{((game_pitch_count - 1) // 20 + 1) * 20}"
                    
                    pitch_count_outcomes[pitch_range]["total"] += 1
                    if pitch.get("velocity"):
                        pitch_count_outcomes[pitch_range]["velocity_sum"] += pitch.get("velocity", 0)
                    
                    result = play.get("play_result", "").lower()
                    if any(hit in result for hit in ["single", "double", "triple", "hit", "home run"]):
                        pitch_count_outcomes[pitch_range]["hits"] += 1
        
        # Calculate timing windows
        windows = {}
        for range_key, outcomes in pitch_count_outcomes.items():
            if outcomes["total"] > 0:
                avg_velocity = outcomes["velocity_sum"] / outcomes["total"] if outcomes["velocity_sum"] > 0 else 0
                hit_rate = outcomes["hits"] / outcomes["total"]
                
                windows[range_key] = {
                    "vulnerability_score": hit_rate * 100,
                    "average_velocity": avg_velocity,
                    "hit_rate": hit_rate,
                    "sample_size": outcomes["total"]
                }
        
        return windows
    
    def _analyze_recent_form(self, games: List[Dict], pitcher_name: str) -> Dict:
        """Analyze recent performance trends with enhanced matching and better data quality"""
        if not games:
            return {"trend": "unknown", "last_3_games_era": 0, "last_3_games_hr_rate": 0, "games_analyzed": 0, "sample_quality": "insufficient"}
        
        recent_games = games[:5]  # Analyze more games for better trends
        total_batters_faced = 0
        total_hits_allowed = 0
        total_hrs_allowed = 0
        total_walks = 0
        total_strikeouts = 0
        games_with_data = 0
        
        for game in recent_games:
            game_batters = 0
            game_hits = 0
            game_hrs = 0
            game_walks = 0
            game_ks = 0
            
            for play in game.get("plays", []):
                if not self._pitcher_name_matches(pitcher_name, play.get("pitcher", "")):
                    continue
                    
                game_batters += 1
                result = play.get("play_result", "").lower()
                
                if any(hr_term in result for hr_term in ["home run", "homer", "hr"]):
                    game_hrs += 1
                elif any(hit_term in result for hit_term in ["single", "double", "triple", "hit", "line drive"]):
                    game_hits += 1
                elif any(walk_term in result for walk_term in ["walk", "walked", "base on balls"]):
                    game_walks += 1
                elif any(k_term in result for k_term in ["strikeout", "struck out"]):
                    game_ks += 1
            
            if game_batters > 0:  # Only count games where pitcher actually appeared
                total_batters_faced += game_batters
                total_hits_allowed += game_hits
                total_hrs_allowed += game_hrs
                total_walks += game_walks
                total_strikeouts += game_ks
                games_with_data += 1
        
        if games_with_data == 0 or total_batters_faced < 5:
            return {
                "trend": "insufficient_data", 
                "games_analyzed": games_with_data,
                "sample_quality": "insufficient",
                "batters_faced": total_batters_faced
            }
        
        # Calculate rates
        hr_rate = total_hrs_allowed / games_with_data if games_with_data > 0 else 0
        hit_rate = total_hits_allowed / total_batters_faced if total_batters_faced > 0 else 0
        walk_rate = total_walks / total_batters_faced if total_batters_faced > 0 else 0
        k_rate = total_strikeouts / total_batters_faced if total_batters_faced > 0 else 0
        
        # Determine trend based on multiple factors
        concerning_factors = 0
        positive_factors = 0
        
        if hr_rate > 1.5:  # More than 1.5 HR per game
            concerning_factors += 2
        elif hr_rate > 1.0:
            concerning_factors += 1
        elif hr_rate < 0.5:
            positive_factors += 1
            
        if hit_rate > 0.35:  # High hit rate
            concerning_factors += 1
        elif hit_rate < 0.25:
            positive_factors += 1
            
        if walk_rate > 0.12:  # High walk rate
            concerning_factors += 1
        elif walk_rate < 0.08:
            positive_factors += 1
            
        if k_rate > 0.25:  # Good strikeout rate
            positive_factors += 1
        elif k_rate < 0.15:
            concerning_factors += 1
        
        # Determine overall trend
        if concerning_factors >= 3:
            trend = "declining"
        elif concerning_factors >= 2:
            trend = "concerning"
        elif positive_factors >= 2:
            trend = "improving"
        else:
            trend = "stable"
            
        sample_quality = "good" if total_batters_faced >= 25 else "limited" if total_batters_faced >= 10 else "poor"
        
        return {
            "trend": trend,
            "hr_rate_per_game": round(hr_rate, 2),
            "hit_rate": round(hit_rate, 3),
            "walk_rate": round(walk_rate, 3),
            "strikeout_rate": round(k_rate, 3),
            "games_analyzed": games_with_data,
            "batters_faced": total_batters_faced,
            "sample_quality": sample_quality,
            "concerning_factors": concerning_factors,
            "positive_factors": positive_factors
        }
    
    def _calculate_overall_vulnerability(self, analysis: Dict) -> float:
        """Calculate overall vulnerability score from all components"""
        score = 0
        weights = {
            "pitch_vulnerabilities": 0.3,
            "inning_patterns": 0.2,
            "pattern_recognition": 0.2,
            "timing_windows": 0.15,
            "recent_form": 0.15
        }
        
        # Pitch vulnerabilities contribution
        if analysis["pitch_vulnerabilities"]:
            max_vuln = max([v["vulnerability_score"] for v in analysis["pitch_vulnerabilities"].values()])
            score += max_vuln * weights["pitch_vulnerabilities"]
        
        # Inning patterns contribution
        if analysis["inning_patterns"]:
            avg_vuln = sum([v["vulnerability_score"] for v in analysis["inning_patterns"].values()]) / len(analysis["inning_patterns"])
            score += avg_vuln * weights["inning_patterns"]
        
        # Pattern recognition contribution
        if analysis["pattern_recognition"]:
            score += analysis["pattern_recognition"]["predictability_score"] * weights["pattern_recognition"]
        
        # Timing windows contribution
        if analysis["timing_windows"]:
            late_game_vuln = max([v["vulnerability_score"] for k, v in analysis["timing_windows"].items() if "61" in k or "81" in k], default=0)
            score += late_game_vuln * weights["timing_windows"]
        
        # Recent form contribution
        if analysis["recent_form"]["trend"] == "declining":
            score += 80 * weights["recent_form"]
        elif analysis["recent_form"]["trend"] == "concerning":
            score += 50 * weights["recent_form"]
        else:
            score += 20 * weights["recent_form"]
        
        return min(100, max(0, score))
    
    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure"""
        return {
            "pitcher_name": "",
            "games_analyzed": 0,
            "pitch_vulnerabilities": {},
            "inning_patterns": {},
            "count_weaknesses": {},
            "position_vulnerabilities": {},
            "pattern_recognition": {"predictability_score": 0, "top_sequences": []},
            "timing_windows": {},
            "recent_form": {"trend": "unknown"},
            "overall_vulnerability_score": 0
        }