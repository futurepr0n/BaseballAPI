import pandas as pd
import os
import shlex
from datetime import datetime

def format_prediction_result(prediction, rank=None, include_details=True, detailed_pitches=False):
    """
    Format a single prediction result for display.
    Returns a multi-line string with formatted prediction information.
    """
    if not prediction:
        return "No prediction data available."
    
    # Basic prediction info
    prefix = f"{rank}. " if rank is not None else ""
    output = [
        f"\n{prefix}{prediction['batter_name']} ({prediction['batter_hand']}) vs {prediction['pitcher_name']} ({prediction['pitcher_hand']}) - HR Score: {prediction['score']:.2f}{prediction.get('details', {}).get('batter_pa_warning', '')}"
    ]
    
    # Team info
    output.append(f"   Batter Team (Opponent): {prediction['batter_team']} | Pitcher's Team: {prediction['pitcher_team']}")
    
    # Score components
    comp_scores = prediction['matchup_components']
    output.append(f"   Components: ArsenalM:{comp_scores.get('arsenal_matchup', 0):.1f}|BatterO:{comp_scores.get('batter_overall', 0):.1f}|PitcherO:{comp_scores.get('pitcher_overall', 0):.1f}|HistCSV:{comp_scores.get('historical_yoy_csv', 0):.1f}|RecentDaily:{comp_scores.get('recent_daily_games', 0):.1f}|Context:{comp_scores.get('contextual', 0):.1f}")
    
    # Outcome probabilities
    outcome_probs = prediction['outcome_probabilities']
    output.append(f"   Probabilities: HR {outcome_probs.get('homerun', 0):.1f}% | Hit {outcome_probs.get('hit', 0):.1f}% | Base {outcome_probs.get('reach_base', 0):.1f}% | K {outcome_probs.get('strikeout', 0):.1f}%")
    
    # Detailed breakdown if requested
    if include_details:
        context_details = prediction.get('details', {})
        
        # Due factors
        due_factor_str = ""
        if 'ab_since_last_hr' in context_details:
            due_factor_str += f" ABs/HR: {context_details['ab_since_last_hr']}/{context_details.get('expected_ab_per_hr', 'N/A')} (Raw AB Due: {context_details.get('due_for_hr_ab_raw_score', 0):.1f})"
        if 'h_since_last_hr' in context_details:
            due_factor_str += f" | Hits/HR: {context_details['h_since_last_hr']}/{context_details.get('expected_h_per_hr', 'N/A')} (Raw Hits Due: {context_details.get('due_for_hr_hits_raw_score', 0):.1f})"
        if due_factor_str:
            output.append(f"   DueFactors:{due_factor_str}")
        
        # Contact trend
        if 'contact_trend' in context_details:
            output.append(f"   Contact Trend: {context_details['contact_trend']} (Raw Scores H:{context_details.get('heating_up_contact_raw_score', 0):.1f}/C:{context_details.get('cold_batter_contact_raw_score', 0):.1f})")
        
        # Historical metrics
        if 'historical_metrics' in context_details and context_details['historical_metrics']:
            hist_metrics = context_details['historical_metrics']
            metrics_info = []
            for metric in hist_metrics:
                metrics_info.append(f"{metric['metric']} {metric['direction']} ({metric['early_value']} → {metric['recent_value']})")
            output.append(f"   Historical Trends: {', '.join(metrics_info)}")
        
        # Recent performance
        if 'recent_N_games_raw_data' in prediction:
            recent_data = prediction['recent_N_games_raw_data']
            games_data = recent_data.get('games_list', [])
            if games_data:
                recent_games_str = f"   Recent Games: "
                for i, game in enumerate(games_data[:3]):  # Show up to 3 recent games
                    if i > 0:
                        recent_games_str += " | "
                    recent_games_str += f"{game['date']}: {game['H']}/{game['AB']}"
                    if game['HR'] > 0:
                        recent_games_str += f", {game['HR']} HR"
                output.append(recent_games_str)
        
        # Pitch arsenal details
        if detailed_pitches and 'arsenal_analysis' in context_details:
            arsenal = context_details['arsenal_analysis']
            if 'pitch_matchups' in arsenal and arsenal['pitch_matchups']:
                output.append(f"\n   --- Pitch Arsenal Breakdown ---")
                for pitch in arsenal['pitch_matchups']:
                    pitch_type = pitch['pitch_type']
                    pitch_name = pitch.get('pitch_name', pitch_type)
                    usage = pitch['usage']
                    stats = pitch.get('current_year_stats', {})
                    
                    output.append(f"   {pitch_name} ({pitch_type}) - {usage:.1f}% usage:")
                    hitter_slg = stats.get('hitter_slg')
                    pitcher_slg = stats.get('pitcher_slg')
                    
                    if hitter_slg is not None:
                        output.append(f"     • Batter SLG: {hitter_slg:.3f}")
                    if pitcher_slg is not None:
                        output.append(f"     • Pitcher SLG allowed: {pitcher_slg:.3f}")
                        
                    hitter_hh = stats.get('hitter_hard_hit_percent')
                    if hitter_hh is not None:
                        output.append(f"     • Batter Hard Hit%: {hitter_hh*100:.1f}%")
    
    return "\n".join(output)

def format_detailed_matchup_report(prediction):
    """
    Generate a more comprehensive report for a single matchup.
    Returns a multi-line string with detailed analysis.
    """
    if not prediction:
        return "No prediction data available."
    
    output = [
        f"\n=== Detailed Matchup Analysis ===",
        f"Batter: {prediction['batter_name']} ({prediction['batter_team']}) - {prediction['batter_hand']} handed",
        f"Pitcher: {prediction['pitcher_name']} ({prediction['pitcher_team']}) - {prediction['pitcher_hand']} handed",
        f"HR Likelihood Score: {prediction['score']:.2f}{prediction.get('details', {}).get('batter_pa_warning', '')}",
        f"\n--- Score Components ---"
    ]
    
    # Score components
    comp_scores = prediction['matchup_components']
    components = [
        f"• Arsenal Matchup: {comp_scores.get('arsenal_matchup', 0):.1f}",
        f"• Batter Overall: {comp_scores.get('batter_overall', 0):.1f}",
        f"• Pitcher Overall: {comp_scores.get('pitcher_overall', 0):.1f}",
        f"• Historical YOY CSV: {comp_scores.get('historical_yoy_csv', 0):.1f}",
        f"• Recent Daily Games: {comp_scores.get('recent_daily_games', 0):.1f}",
        f"• Contextual Factors: {comp_scores.get('contextual', 0):.1f}"
    ]
    output.extend(components)
    
    # Outcome probabilities
    output.append(f"\n--- Outcome Probabilities ---")
    probs = prediction['outcome_probabilities']
    output.extend([
        f"• Home Run: {probs.get('homerun', 0):.1f}%",
        f"• Any Hit: {probs.get('hit', 0):.1f}%",
        f"• Reach Base: {probs.get('reach_base', 0):.1f}%",
        f"• Strikeout: {probs.get('strikeout', 0):.1f}%"
    ])
    
    # Historical analysis
    context_details = prediction.get('details', {})
    if 'historical_metrics' in context_details and context_details['historical_metrics']:
        output.append(f"\n--- Historical Trends ---")
        hist_metrics = context_details['historical_metrics']
        for metric in hist_metrics:
            output.append(f"• {metric['metric'].upper()}: {metric['direction'].title()} from {metric['early_value']} to {metric['recent_value']} (change: {metric['magnitude']:.3f})")
    
    # Due factors
    output.append(f"\n--- HR Due Factors ---")
    if 'ab_since_last_hr' in context_details:
        output.append(f"• At Bats Since Last HR: {context_details['ab_since_last_hr']} (Expected: {context_details.get('expected_ab_per_hr', 'N/A')})")
        output.append(f"  Due Factor Score: {context_details.get('due_for_hr_ab_raw_score', 0):.1f}")
    if 'h_since_last_hr' in context_details:
        output.append(f"• Hits Since Last HR: {context_details['h_since_last_hr']} (Expected: {context_details.get('expected_h_per_hr', 'N/A')})")
        output.append(f"  Due Factor Score: {context_details.get('due_for_hr_hits_raw_score', 0):.1f}")
    
    # Contact trend
    if 'contact_trend' in context_details:
        output.append(f"\n--- Recent Contact Analysis ---")
        output.append(f"• Status: {context_details['contact_trend']}")
        output.append(f"• Heating Up Score: {context_details.get('heating_up_contact_raw_score', 0):.1f}")
        output.append(f"• Cold Batter Score: {context_details.get('cold_batter_contact_raw_score', 0):.1f}")
    
    # Recent performance
    if 'recent_N_games_raw_data' in prediction:
        output.append(f"\n--- Recent Game Performance ---")
        recent_data = prediction['recent_N_games_raw_data']
        trends = recent_data.get('trends_summary_obj', {})
        games_data = recent_data.get('games_list', [])
        
        if trends:
            output.append(f"• Games Analyzed: {trends.get('total_games', 0)}")
            output.append(f"• Recent Avg: {trends.get('avg_avg', 0):.3f}")
            output.append(f"• Recent HR Rate: {trends.get('hr_rate', 0):.3f}")
            output.append(f"• Recent HR/PA: {trends.get('hr_per_pa', 0):.3f}")
            
            if 'trend_direction' in trends:
                output.append(f"• Trend Direction: {trends['trend_direction'].title()}")
                output.append(f"• Trend Metric: {trends.get('trend_metric', 'N/A')}")
                output.append(f"• Early Value: {trends.get('trend_early_val', 'N/A')}")
                output.append(f"• Recent Value: {trends.get('trend_recent_val', 'N/A')}")
        
        if games_data:
            output.append(f"\n--- Last {len(games_data)} Games ---")
            for i, game in enumerate(games_data):
                output.append(f"• {game['date']}: {game['H']}/{game['AB']} ({game['AVG']:.3f}), {game['HR']} HR, {game['BB']} BB, {game['K']} K")
    
    # Pitch arsenal details
    if 'arsenal_analysis' in context_details:
        arsenal = context_details['arsenal_analysis']
        if 'pitch_matchups' in arsenal and arsenal['pitch_matchups']:
            output.append(f"\n--- Pitch Arsenal Analysis ---")
            
            # Overall arsenal metrics
            overall = arsenal.get('overall_summary_metrics', {})
            if overall:
                output.append("Arsenal Overall Metrics:")
                if 'hitter_avg_slg' in overall:
                    output.append(f"• Batter Weighted SLG vs Arsenal: {overall['hitter_avg_slg']:.3f}")
                if 'pitcher_avg_slg' in overall:
                    output.append(f"• Pitcher Weighted SLG Allowed: {overall['pitcher_avg_slg']:.3f}")
            
            # Individual pitches
            output.append("\nIndividual Pitches:")
            for pitch in arsenal['pitch_matchups']:
                pitch_type = pitch['pitch_type']
                pitch_name = pitch.get('pitch_name', pitch_type)
                usage = pitch['usage']
                stats = pitch.get('current_year_stats', {})
                
                output.append(f"\n• {pitch_name} ({pitch_type}) - {usage:.1f}% usage:")
                
                # Batter stats against this pitch
                output.append("  Batter vs This Pitch:")
                for stat_key, stat_val in stats.items():
                    if stat_key.startswith('hitter_') and stat_val is not None:
                        stat_name = stat_key.replace('hitter_', '')
                        if 'percent' in stat_key:
                            output.append(f"    - {stat_name}: {stat_val*100:.1f}%")
                        else:
                            output.append(f"    - {stat_name}: {stat_val:.3f}")
                
                # Pitcher stats with this pitch
                output.append("  Pitcher with This Pitch:")
                for stat_key, stat_val in stats.items():
                    if stat_key.startswith('pitcher_') and stat_val is not None:
                        stat_name = stat_key.replace('pitcher_', '')
                        if 'percent' in stat_key:
                            output.append(f"    - {stat_name}: {stat_val*100:.1f}%")
                        else:
                            output.append(f"    - {stat_name}: {stat_val:.3f}")
    
    return "\n".join(output)

def create_predictions_csv(predictions, filename=None):
    """
    Create a CSV file with detailed prediction data.
    Returns the filename of the created CSV.
    """
    if not predictions:
        return None
    
    summary_data = []
    
    for rank_index, pred_data in enumerate(predictions):
        details = pred_data.get('details', {})
        recent_data = pred_data.get('recent_N_games_raw_data', {})
        recent_trends = recent_data.get('trends_summary_obj', {})
        
        csv_row = {
            'Rank': rank_index + 1,
            'Batter': pred_data['batter_name'], 
            'Batter_Team': pred_data['batter_team'], 
            'B_Hand': pred_data['batter_hand'],
            'Pitcher': pred_data['pitcher_name'], 
            'Pitcher_Team': pred_data['pitcher_team'], 
            'P_Hand': pred_data['pitcher_hand'],
            'HR_Score': pred_data['score'],
            'PA_2025': details.get('batter_pa_2025', 0),
            'HR_Prob': pred_data['outcome_probabilities']['homerun'],
            'Hit_Prob': pred_data['outcome_probabilities']['hit'],
            'OB_Prob': pred_data['outcome_probabilities']['reach_base'],
            'K_Prob': pred_data['outcome_probabilities']['strikeout'],
            'AB_since_HR': details.get('ab_since_last_hr', 'N/A'), 
            'Exp_AB_HR': details.get('expected_ab_per_hr', 'N/A'), 
            'AB_Due_Score': details.get('due_for_hr_ab_raw_score', 'N/A'),
            'H_since_HR': details.get('h_since_last_hr', 'N/A'), 
            'Exp_H_HR': details.get('expected_h_per_hr', 'N/A'), 
            'H_Due_Score': details.get('due_for_hr_hits_raw_score', 'N/A'),
            'Contact_Trend': details.get('contact_trend', 'N/A'), 
            'Heat_Score': details.get('heating_up_contact_raw_score', 'N/A'), 
            'Cold_Score': details.get('cold_batter_contact_raw_score', 'N/A'),
            'ISO_2024': details.get('iso_2024', 'N/A'),
            'ISO_2025': details.get('iso_2025_adj_for_trend', 'N/A'),
            'ISO_Trend': details.get('iso_trend_2025v2024', 'N/A'),
            'Recent_Trend_Dir': recent_trends.get('trend_direction', 'N/A'),
            'Recent_HR_Rate': recent_trends.get('hr_rate', 'N/A'),
            'Recent_AVG': recent_trends.get('avg_avg', 'N/A'),
            'Recent_Games': recent_trends.get('total_games', 'N/A')
        }
        
        # Add arsenal analysis metrics if available
        arsenal_summary = details.get('arsenal_analysis', {}).get('overall_summary_metrics', {})
        if arsenal_summary:
            csv_row['H_Wtd_SLG_vs_Ars'] = arsenal_summary.get('hitter_avg_slg', 'N/A')
            csv_row['P_Wtd_SLG_A_w_Ars'] = arsenal_summary.get('pitcher_avg_slg', 'N/A')
        
        # Add component scores
        components = pred_data.get('matchup_components', {})
        for comp_name, comp_value in components.items():
            csv_row[f'Comp_{comp_name}'] = comp_value
        
        summary_data.append(csv_row)
    
    # Create DataFrame and save to CSV
    df_results = pd.DataFrame(summary_data)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"predictions_{timestamp}.csv"
    
    df_results.to_csv(filename, index=False, float_format='%.3f')
    print(f"\nDetailed results saved to CSV: {filename}")
    
    return filename

def process_matchup_batch_file(filepath):
    """
    Process a batch file containing matchup specifications.
    Returns a list of (pitcher_name, team_abbr) tuples.
    """
    matchups = []
    
    if not os.path.exists(filepath):
        print(f"ERROR: Batch file not found: {filepath}")
        return matchups
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f_in:
            for line_num, line in enumerate(f_in, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    parts = shlex.split(line)
                    if len(parts) == 2:
                        pitcher_name, team_abbr = parts[0], parts[1]
                        
                        # Basic validation
                        if not (len(team_abbr) >= 2 and team_abbr.isupper()):
                            print(f"Warning: Line {line_num}: '{line}' - Team '{team_abbr}' invalid (should be 3 uppercase letters). Skipping.")
                            continue
                            
                        matchups.append((pitcher_name, team_abbr))
                    else:
                        print(f"Warning: Malformed line {line_num}: '{line}'. Expected format: 'Pitcher Name' TEAM. Skipping.")
                except Exception as e:
                    print(f"Error processing line {line_num} ('{line}'): {e}")
    except Exception as e:
        print(f"ERROR: Could not read batch file {filepath}: {e}")
    
    return matchups

def print_top_predictions(predictions, limit=15, detailed=False):
    """
    Print the top N predictions from a list.
    """
    if not predictions:
        print("No predictions to display.")
        return
    
    print(f"\n=== Top {min(limit, len(predictions))} HR Predictions ===")
    print("=" * 70)
    
    for i, pred in enumerate(predictions[:limit], 1):
        if detailed:
            print(format_detailed_matchup_report(pred))
            print("-" * 70)
        else:
            print(format_prediction_result(pred, i))
            print("-" * 70)
    
    # Print summary of total predictions
    if len(predictions) > limit:
        print(f"\nDisplayed top {limit} of {len(predictions)} total predictions. Use --all to see all or check the CSV output.")

def generate_combined_report(all_matchups_data, filename_prefix="combined_analysis"):
    """
    Generate a combined report for all matchups.
    Returns the filename of the created CSV.
    """
    if not all_matchups_data:
        return None
    
    # Flatten all predictions into a single list
    all_predictions = []
    for matchup_info in all_matchups_data:
        all_predictions.extend(matchup_info['predictions'])
    
    # Note: Predictions should already be sorted in the individual matchup processing
    # This preserves the sorting criteria used in the original analysis
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"{filename_prefix}_{timestamp}.csv"
    
    # Generate CSV
    create_predictions_csv(all_predictions, csv_filename)
    
    # Print top predictions
    print(f"\n\n--- Combined Top Predictions from All {len(all_matchups_data)} Processed Matchups ---")
    print_top_predictions(all_predictions, limit=20)
    
    return csv_filename