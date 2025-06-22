"""
Enhanced data handling for BaseballAPI with missing pitcher data fallbacks.
Provides robust analysis even when Baseball Savant scraping fails.
"""

import numpy as np
import pandas as pd
from collections import defaultdict
import logging
from typing import Dict, List, Optional, Tuple, Any

from enhanced_analyzer import (
    calculate_league_averages_by_pitch_type,
    enhanced_arsenal_matchup_with_fallbacks,
    enhanced_hr_score_with_missing_data_handling,
    LEAGUE_AVERAGE_PITCH_DISTRIBUTION,
    LEAGUE_AVERAGE_PERFORMANCE_BY_PITCH
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDataHandler:
    """
    Handles missing pitcher data scenarios with multiple fallback strategies.
    """
    
    def __init__(self, master_player_data: Dict, league_avg_stats: Dict, metric_ranges: Dict, 
                 daily_data: Dict = None, roster_data: List = None):
        self.master_player_data = master_player_data
        self.league_avg_stats = league_avg_stats
        self.metric_ranges = metric_ranges
        self.daily_data = daily_data or {}
        self.roster_data = roster_data or []
        
        # Calculate real-time league averages by pitch type
        self.league_avg_by_pitch_type = calculate_league_averages_by_pitch_type(master_player_data)
        
        # Statistics tracking
        self.analysis_stats = {
            'total_analyses': 0,
            'full_data_analyses': 0,
            'partial_data_analyses': 0,
            'team_based_analyses': 0,
            'league_average_analyses': 0,
            'failed_analyses': 0
        }
        
        logger.info(f"Enhanced data handler initialized with {len(master_player_data)} players")
    
    def analyze_team_matchup_with_fallbacks(self, pitcher_name: str, team_abbr: str, 
                                          sort_by: str = 'score', min_score: float = 0,
                                          include_confidence_metrics: bool = True) -> Dict[str, Any]:
        """
        Analyze pitcher vs team matchup with robust missing data handling.
        
        Args:
            pitcher_name: Name of the pitcher
            team_abbr: Team abbreviation (e.g., 'SEA', 'NYY')
            sort_by: Field to sort results by
            min_score: Minimum score threshold
            include_confidence_metrics: Whether to include data quality metrics
            
        Returns:
            Dictionary containing analysis results with confidence indicators
        """
        # Find pitcher
        pitcher_data = self._find_pitcher_by_name(pitcher_name)
        if not pitcher_data:
            return {
                'error': f"Pitcher '{pitcher_name}' not found",
                'success': False,
                'confidence': 0.0,
                'data_source': 'none'
            }
        
        pitcher_id = pitcher_data['pitcher_id']
        
        # Find team batters
        team_batters = self._find_team_batters(team_abbr)
        if not team_batters:
            return {
                'error': f"No batters found for team '{team_abbr}'",
                'success': False,
                'confidence': 0.0,
                'data_source': 'none'
            }
        
        # Analyze each batter vs pitcher
        batter_analyses = []
        total_confidence = 0
        data_source_counts = defaultdict(int)
        
        for batter in team_batters:
            try:
                # Get recent performance for this batter
                recent_stats = self._get_recent_batter_performance(batter['batter_id'])
                
                # Perform enhanced analysis
                analysis = enhanced_hr_score_with_missing_data_handling(
                    batter['batter_id'],
                    pitcher_id,
                    self.master_player_data,
                    {},  # historical_data - could be populated if available
                    self.metric_ranges,
                    self.league_avg_stats,
                    self.league_avg_by_pitch_type,
                    recent_stats
                )
                
                if analysis.get('score', 0) >= min_score:
                    analysis['player_id'] = batter['batter_id']
                    analysis['team'] = team_abbr.upper()
                    batter_analyses.append(analysis)
                    
                    # Track statistics
                    total_confidence += analysis.get('confidence', 0)
                    data_source_counts[analysis.get('data_source', 'unknown')] += 1
                    self.analysis_stats['total_analyses'] += 1
                    
                    # Categorize analysis type
                    confidence = analysis.get('confidence', 0)
                    if confidence >= 0.8:
                        self.analysis_stats['full_data_analyses'] += 1
                    elif confidence >= 0.5:
                        self.analysis_stats['partial_data_analyses'] += 1
                    elif confidence >= 0.3:
                        self.analysis_stats['team_based_analyses'] += 1
                    else:
                        self.analysis_stats['league_average_analyses'] += 1
                
            except Exception as e:
                logger.error(f"Error analyzing batter {batter.get('name', 'unknown')}: {e}")
                self.analysis_stats['failed_analyses'] += 1
                continue
        
        # Sort results using the unified sort utility
        if batter_analyses:
            from sort_utils import sort_predictions
            batter_analyses = sort_predictions(batter_analyses, sort_by=sort_by, ascending=False)
        
        # Calculate overall analysis quality metrics
        avg_confidence = total_confidence / len(batter_analyses) if batter_analyses else 0
        primary_data_source = max(data_source_counts.items(), key=lambda x: x[1])[0] if data_source_counts else 'none'
        
        # Determine overall reliability
        if avg_confidence >= 0.7:
            reliability = 'high'
        elif avg_confidence >= 0.4:
            reliability = 'medium'
        else:
            reliability = 'low'
        
        result = {
            'success': True,
            'pitcher_name': pitcher_name,
            'pitcher_id': pitcher_id,
            'team': team_abbr.upper(),
            'predictions': batter_analyses,
            'total_batters_analyzed': len(batter_analyses),
            'average_confidence': round(avg_confidence, 3),
            'primary_data_source': primary_data_source,
            'reliability': reliability,
            'sort_by': sort_by,
            'min_score_filter': min_score
        }
        
        if include_confidence_metrics:
            result['data_quality_breakdown'] = {
                'data_source_distribution': dict(data_source_counts),
                'analysis_summary': {
                    'full_pitcher_data': data_source_counts.get('pitcher_specific', 0),
                    'partial_pitcher_data': data_source_counts.get('pitcher_partial', 0),
                    'team_based_estimates': data_source_counts.get('team_based', 0),
                    'league_average_fallbacks': data_source_counts.get('league_average', 0)
                },
                'confidence_distribution': self._calculate_confidence_distribution(batter_analyses),
                'missing_data_impact': self._assess_missing_data_impact(avg_confidence, primary_data_source)
            }
        
        return result
    
    def _find_pitcher_by_name(self, pitcher_name: str) -> Optional[Dict[str, Any]]:
        """Find pitcher by name in master player data."""
        for pid, pdata in self.master_player_data.items():
            roster_info = pdata.get('roster_info', {})
            if roster_info.get('type') == 'pitcher':
                names_to_check = [
                    roster_info.get('fullName_resolved', ''),
                    roster_info.get('fullName_cleaned', ''),
                    roster_info.get('name_cleaned', ''),
                    roster_info.get('name', '')
                ]
                
                for name in names_to_check:
                    if name and name.lower() == pitcher_name.lower():
                        return {
                            'pitcher_id': pid,
                            'name': roster_info.get('fullName_resolved', pitcher_name),
                            'team': roster_info.get('team', 'UNK')
                        }
        
        return None
    
    def _find_team_batters(self, team_abbr: str) -> List[Dict[str, Any]]:
        """Find all batters for a given team."""
        batters = []
        
        for pid, pdata in self.master_player_data.items():
            roster_info = pdata.get('roster_info', {})
            if (roster_info.get('type') == 'hitter' and 
                roster_info.get('team', '').upper() == team_abbr.upper()):
                
                batters.append({
                    'batter_id': pid,
                    'name': roster_info.get('fullName_resolved', f"Player_{pid}"),
                    'team': team_abbr.upper(),
                    'bats': roster_info.get('bats', 'R')
                })
        
        return batters
    
    def _get_recent_batter_performance(self, batter_id: str) -> Optional[Dict[str, Any]]:
        """Get recent performance stats for a batter using proper data if available."""
        # Try to get actual recent performance from daily data if available
        batter_data = self.master_player_data.get(batter_id, {})
        roster_info = batter_data.get('roster_info', {})
        batter_resolved_name = roster_info.get('fullName_resolved')
        
        if batter_resolved_name:
            try:
                # Import the proper functions
                from data_loader import get_last_n_games_performance
                from analyzer import calculate_recent_trends
                
                # Try to get recent games data if daily data is available
                # For now, we'll use the enhanced data handler's global data
                daily_data = getattr(self, 'daily_data', {})
                roster_data = getattr(self, 'roster_data', [])
                
                if daily_data and roster_data:
                    recent_games, _ = get_last_n_games_performance(
                        batter_resolved_name, daily_data, roster_data, n_games=7
                    )
                    
                    if recent_games:
                        recent_trends = calculate_recent_trends(recent_games)
                        return recent_trends
            except ImportError:
                pass
        
        # Fallback to aggregated stats calculation
        stats_2025 = batter_data.get('stats_2025_aggregated', {})
        
        if not stats_2025:
            return None
        
        # Simulate recent performance calculation
        total_games = stats_2025.get('G', 0)
        if total_games < 2:
            return None
        
        # Create a reasonable approximation
        total_ab = stats_2025.get('AB', 0)
        total_hits = stats_2025.get('H', 0)
        total_hrs = stats_2025.get('HR', 0)
        total_bb = stats_2025.get('BB', 0)
        total_pa = stats_2025.get('PA_approx', 0)
        
        avg_avg = total_hits / total_ab if total_ab > 0 else 0
        hr_per_pa = total_hrs / total_pa if total_pa > 0 else 0
        hit_rate = total_hits / total_ab if total_ab > 0 else 0
        
        return {
            'total_games': min(total_games, 7),  # Simulate last 7 games
            'total_ab': total_ab,
            'total_hits': total_hits,
            'total_hrs': total_hrs,
            'total_bb': total_bb,
            'total_k': stats_2025.get('K', 0),
            'total_pa_approx': total_pa,
            'hit_rate': hit_rate,
            'hr_per_pa': hr_per_pa,
            'hr_rate': hr_per_pa,  # Alias for consistency
            'avg_avg': avg_avg,
            'avg_obp': (total_hits + total_bb) / total_pa if total_pa > 0 else 0,
            'obp_calc': (total_hits + total_bb) / total_pa if total_pa > 0 else 0,
            'trend_direction': 'stable',  # Would be calculated from actual recent games
            'trend_magnitude': 0.0,
            'trend_early_val': hr_per_pa * 0.9,  # Simulate slight improvement trend
            'trend_recent_val': hr_per_pa * 1.1,
            'trend_metric': 'HR_per_PA'
        }
    
    def _calculate_confidence_distribution(self, analyses: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of confidence levels."""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for analysis in analyses:
            confidence = analysis.get('confidence', 0)
            if confidence >= 0.7:
                distribution['high'] += 1
            elif confidence >= 0.4:
                distribution['medium'] += 1
            else:
                distribution['low'] += 1
        
        return distribution
    
    def _assess_missing_data_impact(self, avg_confidence: float, primary_data_source: str) -> Dict[str, Any]:
        """Assess the impact of missing data on analysis quality."""
        impact_assessment = {
            'severity': 'low',
            'description': 'Full pitcher data available for most analyses',
            'recommendations': []
        }
        
        if primary_data_source == 'league_average':
            impact_assessment['severity'] = 'high'
            impact_assessment['description'] = 'Most analyses rely on league average fallbacks due to missing pitcher data'
            impact_assessment['recommendations'] = [
                'Consider using alternative data sources for pitcher information',
                'Implement pitcher historical data backfill',
                'Use team-based pitching profiles when available'
            ]
        elif primary_data_source == 'team_based':
            impact_assessment['severity'] = 'medium'
            impact_assessment['description'] = 'Analyses use team-based estimates due to limited individual pitcher data'
            impact_assessment['recommendations'] = [
                'Enhance pitcher-specific data collection',
                'Validate team-based estimates against available individual data'
            ]
        elif primary_data_source == 'pitcher_partial':
            impact_assessment['severity'] = 'low'
            impact_assessment['description'] = 'Partial pitcher data available, supplemented with league averages'
            impact_assessment['recommendations'] = [
                'Monitor data completeness for key pitchers',
                'Consider historical data to fill gaps'
            ]
        
        if avg_confidence < 0.5:
            impact_assessment['severity'] = max(impact_assessment['severity'], 'medium')
            impact_assessment['recommendations'].append('Consider displaying confidence warnings to users')
        
        return impact_assessment
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get statistics about analyses performed."""
        total = self.analysis_stats['total_analyses']
        if total == 0:
            return {'message': 'No analyses performed yet'}
        
        return {
            'total_analyses': total,
            'success_rate': round((total - self.analysis_stats['failed_analyses']) / total * 100, 1),
            'data_quality_breakdown': {
                'full_data_percentage': round(self.analysis_stats['full_data_analyses'] / total * 100, 1),
                'partial_data_percentage': round(self.analysis_stats['partial_data_analyses'] / total * 100, 1),
                'team_based_percentage': round(self.analysis_stats['team_based_analyses'] / total * 100, 1),
                'league_average_percentage': round(self.analysis_stats['league_average_analyses'] / total * 100, 1)
            },
            'recommendations': self._generate_data_quality_recommendations()
        }
    
    def _generate_data_quality_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis statistics."""
        recommendations = []
        total = self.analysis_stats['total_analyses']
        
        if total == 0:
            return recommendations
        
        league_avg_pct = self.analysis_stats['league_average_analyses'] / total
        team_based_pct = self.analysis_stats['team_based_analyses'] / total
        failed_pct = self.analysis_stats['failed_analyses'] / total
        
        if league_avg_pct > 0.5:
            recommendations.append("High reliance on league averages detected - consider improving pitcher data collection")
        
        if team_based_pct > 0.3:
            recommendations.append("Frequent use of team-based estimates - validate against individual pitcher performance")
        
        if failed_pct > 0.1:
            recommendations.append("Analysis failure rate above threshold - investigate data quality issues")
        
        if self.analysis_stats['full_data_analyses'] / total < 0.3:
            recommendations.append("Low percentage of full-data analyses - prioritize complete pitcher arsenal data")
        
        return recommendations

def create_enhanced_analysis_report(analysis_result: Dict[str, Any]) -> str:
    """
    Create a formatted report explaining the analysis quality and missing data handling.
    """
    if not analysis_result.get('success', False):
        return f"Analysis failed: {analysis_result.get('error', 'Unknown error')}"
    
    report_lines = []
    report_lines.append(f"=== Enhanced Analysis Report ===")
    report_lines.append(f"Pitcher: {analysis_result['pitcher_name']}")
    report_lines.append(f"vs Team: {analysis_result['team']}")
    report_lines.append(f"Batters Analyzed: {analysis_result['total_batters_analyzed']}")
    report_lines.append(f"Overall Reliability: {analysis_result['reliability'].upper()}")
    report_lines.append(f"Average Confidence: {analysis_result['average_confidence']:.1%}")
    report_lines.append(f"Primary Data Source: {analysis_result['primary_data_source'].replace('_', ' ').title()}")
    
    if 'data_quality_breakdown' in analysis_result:
        quality = analysis_result['data_quality_breakdown']
        report_lines.append("\n--- Data Quality Breakdown ---")
        
        analysis_summary = quality['analysis_summary']
        if analysis_summary['full_pitcher_data'] > 0:
            report_lines.append(f"✓ Full pitcher data: {analysis_summary['full_pitcher_data']} analyses")
        if analysis_summary['partial_pitcher_data'] > 0:
            report_lines.append(f"~ Partial pitcher data: {analysis_summary['partial_pitcher_data']} analyses")
        if analysis_summary['team_based_estimates'] > 0:
            report_lines.append(f"◦ Team-based estimates: {analysis_summary['team_based_estimates']} analyses")
        if analysis_summary['league_average_fallbacks'] > 0:
            report_lines.append(f"◦ League average fallbacks: {analysis_summary['league_average_fallbacks']} analyses")
        
        if 'missing_data_impact' in quality:
            impact = quality['missing_data_impact']
            report_lines.append(f"\n--- Missing Data Impact ---")
            report_lines.append(f"Severity: {impact['severity'].upper()}")
            report_lines.append(f"Description: {impact['description']}")
            
            if impact['recommendations']:
                report_lines.append("Recommendations:")
                for rec in impact['recommendations']:
                    report_lines.append(f"  • {rec}")
    
    # Top predictions summary
    if analysis_result.get('predictions'):
        report_lines.append("\n--- Top Predictions ---")
        top_predictions = analysis_result['predictions'][:5]
        for i, pred in enumerate(top_predictions, 1):
            confidence_indicator = "🟢" if pred.get('confidence', 0) >= 0.7 else "🟡" if pred.get('confidence', 0) >= 0.4 else "🔴"
            report_lines.append(
                f"{i}. {pred['batter_name']} - Score: {pred['score']:.1f} "
                f"({pred.get('confidence', 0):.1%} confidence {confidence_indicator})"
            )
    
    return "\n".join(report_lines)