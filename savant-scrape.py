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
        },
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/batted-ball?batSide=L&gameType=Regular&minSwings=q&minGroupSwings=1&pitchHand=L&pitchType=FF%7CSI%7CFC%7CCH%7CFS%7CFO%7CSC%7CCU%7CKC%7CCS%7CSL%7CST%7CSV%7CKN&seasonStart=2025&seasonEnd=2025&type=batter&csv=true",
            "filename": "batters-batted-ball-bat-left-pitch-hand-left-2025.csv"
        },
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/batted-ball?batSide=L&gameType=Regular&minSwings=q&minGroupSwings=1&pitchHand=R&pitchType=FF%7CSI%7CFC%7CCH%7CFS%7CFO%7CSC%7CCU%7CSL%7CST%7CSV%7CKN&seasonStart=2025&seasonEnd=2025&type=batter&csv=true",
            "filename": "batters-batted-ball-bat-left-pitch-hand-right-2025"
        },
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/batted-ball?batSide=R&gameType=Regular&minSwings=q&minGroupSwings=1&pitchHand=L&pitchType=FF%7CSI%7CFC%7CCH%7CFS%7CFO%7CSC%7CCU%7CKC%7CCS%7CSL%7CST%7CSV%7CKN&seasonStart=2025&seasonEnd=2025&type=batter&csv=true",
            "filename": "batters-batted-ball-bat-right-pitch-hand-left-2025.csv"
        },
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/batted-ball?batSide=R&gameType=Regular&minSwings=q&minGroupSwings=1&pitchHand=R&pitchType=FF%7CSI%7CFC%7CCH%7CFS%7CFO%7CSC%7CCU%7CSL%7CST%7CSV%7CKN&seasonStart=2025&seasonEnd=2025&type=batter&csv=true",
            "filename": "batters-batted-ball-bat-right-pitch-hand-right-2025.csv"
        }

    ]
    
    # Define the target directories relative to the script's location
    target_dirs = [
        "../BaseballTracker/public/data/stats",
        "../BaseballTracker/build/data/stats"
    ]
    
    for target_dir in target_dirs:
        # Create directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)
        
        for stat in stats_files:
            try:
                # Send GET request to download the file
                response = requests.get(stat["url"])
                response.raise_for_status()  # Raise an error for bad status codes
                
                # Save the file to the target directory
                file_path = os.path.join(target_dir, stat["filename"])
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                    
                print(f"Successfully downloaded and saved as {file_path}")
                
            except requests.RequestException as e:
                print(f"Error downloading {stat['filename']} to {target_dir}: {e}")
            except IOError as e:
                print(f"Error saving {stat['filename']} to {target_dir}: {e}")

    download_mlb_stats()