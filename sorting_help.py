"""
Helper module to display available sorting options.
"""

from sort_utils import get_sort_description

def print_sorting_options():
    """Print all available sorting options for the user."""
    sort_options = {
        # Main prediction score
        'score': 'Overall HR Score',
        
        # Outcome probabilities
        'hr': 'HR Probability',
        'homerun': 'HR Probability',
        'hit': 'Hit Probability',
        'reach_base': 'Reach Base Probability',
        'strikeout': 'Strikeout Probability (lowest first)',
        
        # Component scores
        'arsenal_matchup': 'Arsenal Matchup Component',
        'batter_overall': 'Batter Overall Component',
        'pitcher_overall': 'Pitcher Overall Component',
        'historical_yoy_csv': 'Historical Trend Component',
        'recent_daily_games': 'Recent Performance Component',
        'contextual': 'Contextual Factors Component',
        
        # Recent performance stats
        'recent_avg': 'Recent Batting Average',
        'hr_rate': 'Recent HR Rate',
        'obp': 'Recent On-Base Percentage',
        
        # Due factors
        'ab_due': 'Due for HR (AB-based)',
        'hits_due': 'Due for HR (hits-based)',
        'heating_up': 'Heating Up Contact Score',
        'cold': 'Cold Batter Score',
        
        # Arsenal analysis metrics
        'hitter_slg': 'Hitter SLG vs Arsenal',
        'pitcher_slg': 'Pitcher SLG Allowed'
    }
    
    print("\nAvailable Sorting Options:")
    print("==========================")
    
    categories = {
        "Main Score": ['score'],
        "Outcome Probabilities": ['hr', 'hit', 'reach_base', 'strikeout'],
        "Component Scores": ['arsenal_matchup', 'batter_overall', 'pitcher_overall', 
                            'historical_yoy_csv', 'recent_daily_games', 'contextual'],
        "Recent Performance": ['recent_avg', 'hr_rate', 'obp'],
        "Due Factors": ['ab_due', 'hits_due', 'heating_up', 'cold'],
        "Arsenal Analysis": ['hitter_slg', 'pitcher_slg']
    }
    
    for category, keys in categories.items():
        print(f"\n{category}:")
        for key in keys:
            print(f"  --sort={key:<15} : {sort_options.get(key, 'Custom Sort')}")
    
    print("\nExamples:")
    print("  python main.py --sort=hr \"Sean Burke\" TEX")
    print("  python main.py --sort=recent_avg --ascending \"MacKenzie Gore\" SEA")
    print("  python main.py --sort=heating_up --batch=matchups.txt")

if __name__ == "__main__":
    print_sorting_options()