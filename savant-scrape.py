import requests
import os

def download_mlb_stats():
    # List of URLs and corresponding filenames
    stats_files = [
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/pitch-arsenal-stats?type=batter&pitchType=&year=2025&team=&min=1&minPitches=q&sort=4&sortDir=desc&csv=true",
            "filename": "hitterpitcharsenalstats_2025.csv"
        },
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/pitch-arsenal-stats?type=pitcher&pitchType=&year=2025&team=&min=1&minPitches=q&sort=4&sortDir=desc&csv=true",
            "filename": "pitcherarsenalstats_2025.csv"
        },
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/statcast?type=batter&year=2025&position=&team=&min=q&sort=barrels_per_pa&sortDir=desc&csv=true",
            "filename": "hitter_exit_velocity_2025.csv"
        },
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/statcast?type=pitcher&year=2025&position=&team=&min=q&sort=barrels_per_pa&sortDir=desc&csv=true",
            "filename": "pitcher_exit_velocity_2025.csv"
        }
    ]
    
    for stat in stats_files:
        try:
            # Send GET request to download the file
            response = requests.get(stat["url"])
            response.raise_for_status()  # Raise an error for bad status codes
            
            # Save the file
            with open(stat["filename"], 'wb') as f:
                f.write(response.content)
                
            print(f"Successfully downloaded and saved as {stat['filename']}")
            
        except requests.RequestException as e:
            print(f"Error downloading {stat['filename']}: {e}")
        except IOError as e:
            print(f"Error saving {stat['filename']}: {e}")

if __name__ == "__main__":
    # Create directory if it doesn't exist
    os.makedirs("mlb_stats", exist_ok=True)
    os.chdir("mlb_stats")
    
    download_mlb_stats()