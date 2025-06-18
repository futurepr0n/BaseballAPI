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
            "filename": "batters-batted-ball-bat-left-pitch-hand-right-2025.csv"
        },
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/batted-ball?batSide=R&gameType=Regular&minSwings=q&minGroupSwings=1&pitchHand=L&pitchType=FF%7CSI%7CFC%7CCH%7CFS%7CFO%7CSC%7CCU%7CKC%7CCS%7CSL%7CST%7CSV%7CKN&seasonStart=2025&seasonEnd=2025&type=batter&csv=true",
            "filename": "batters-batted-ball-bat-right-pitch-hand-left-2025.csv"
        },
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/batted-ball?batSide=R&gameType=Regular&minSwings=q&minGroupSwings=1&pitchHand=R&pitchType=FF%7CSI%7CFC%7CCH%7CFS%7CFO%7CSC%7CCU%7CSL%7CST%7CSV%7CKN&seasonStart=2025&seasonEnd=2025&type=batter&csv=true",
            "filename": "batters-batted-ball-bat-right-pitch-hand-right-2025.csv"
        },
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/custom?year=2025&type=batter&filter=&min=10&selections=player_age%2Cab%2Cpa%2Chit%2Csingle%2Cdouble%2Ctriple%2Chome_run%2Cstrikeout%2Cwalk%2Ck_percent%2Cbb_percent%2Cbatting_avg%2Cslg_percent%2Con_base_percent%2Con_base_plus_slg%2Cisolated_power%2Cbabip%2Cb_rbi%2Cb_lob%2Cb_total_bases%2Cr_total_caught_stealing%2Cr_total_stolen_base%2Cb_ab_scoring%2Cb_ball%2Cb_called_strike%2Cb_catcher_interf%2Cb_foul%2Cb_foul_tip%2Cb_game%2Cb_gnd_into_dp%2Cb_gnd_into_tp%2Cb_gnd_rule_double%2Cb_hit_by_pitch%2Cb_hit_ground%2Cb_hit_fly%2Cb_hit_into_play%2Cb_hit_line_drive%2Cb_hit_popup%2Cb_out_fly%2Cb_out_ground%2Cb_out_line_drive%2Cb_out_popup%2Cb_intent_ball%2Cb_intent_walk%2Cb_interference%2Cb_pinch_hit%2Cb_pinch_run%2Cb_pitchout%2Cb_played_dh%2Cb_sac_bunt%2Cb_sac_fly%2Cb_swinging_strike%2Cr_caught_stealing_2b%2Cr_caught_stealing_3b%2Cr_caught_stealing_home%2Cr_defensive_indiff%2Cr_interference%2Cr_pickoff_1b%2Cr_pickoff_2b%2Cr_pickoff_3b%2Cr_run%2Cr_stolen_base_2b%2Cr_stolen_base_3b%2Cr_stolen_base_home%2Cb_total_ball%2Cb_total_sacrifices%2Cb_total_strike%2Cb_total_swinging_strike%2Cb_total_pitches%2Cr_stolen_base_pct%2Cr_total_pickoff%2Cb_reached_on_error%2Cb_walkoff%2Cb_reached_on_int%2Cxba%2Cxslg%2Cwoba%2Cxwoba%2Cxobp%2Cxiso%2Cwobacon%2Cxwobacon%2Cbacon%2Cxbacon%2Cxbadiff%2Cxslgdiff%2Cwobadiff%2Cavg_swing_speed%2Cfast_swing_rate%2Cblasts_contact%2Cblasts_swing%2Csquared_up_contact%2Csquared_up_swing%2Cavg_swing_length%2Cswords%2Cattack_angle%2Cattack_direction%2Cideal_angle_rate%2Cvertical_swing_path%2Cexit_velocity_avg%2Claunch_angle_avg%2Csweet_spot_percent%2Cbarrel%2Cbarrel_batted_rate%2Csolidcontact_percent%2Cflareburner_percent%2Cpoorlyunder_percent%2Cpoorlytopped_percent%2Cpoorlyweak_percent%2Chard_hit_percent%2Cavg_best_speed%2Cavg_hyper_speed%2Cz_swing_percent%2Cz_swing_miss_percent%2Coz_swing_percent%2Coz_swing_miss_percent%2Coz_contact_percent%2Cout_zone_swing_miss%2Cout_zone_swing%2Cout_zone_percent%2Cout_zone%2Cmeatball_swing_percent%2Cmeatball_percent%2Cpitch_count_offspeed%2Cpitch_count_fastball%2Cpitch_count_breaking%2Cpitch_count%2Ciz_contact_percent%2Cin_zone_swing_miss%2Cin_zone_swing%2Cin_zone_percent%2Cin_zone%2Cedge_percent%2Cedge%2Cwhiff_percent%2Cswing_percent%2Cpull_percent%2Cstraightaway_percent%2Copposite_percent%2Cbatted_ball%2Cf_strike_percent%2Cgroundballs_percent%2Cgroundballs%2Cflyballs_percent%2Cflyballs%2Clinedrives_percent%2Clinedrives%2Cpopups_percent%2Cpopups%2Cpop_2b_sba_count%2Cpop_2b_sba%2Cpop_2b_sb%2Cpop_2b_cs%2Cpop_3b_sba_count%2Cpop_3b_sba%2Cpop_3b_sb%2Cpop_3b_cs%2Cexchange_2b_3b_sba%2Cmaxeff_arm_2b_3b_sba%2Cn_outs_above_average%2Cn_fieldout_5stars%2Cn_opp_5stars%2Cn_5star_percent%2Cn_fieldout_4stars%2Cn_opp_4stars%2Cn_4star_percent%2Cn_fieldout_3stars%2Cn_opp_3stars%2Cn_3star_percent%2Cn_fieldout_2stars%2Cn_opp_2stars%2Cn_2star_percent%2Cn_fieldout_1stars%2Cn_opp_1stars%2Cn_1star_percent%2Crel_league_reaction_distance%2Crel_league_burst_distance%2Crel_league_routing_distance%2Crel_league_bootup_distance%2Cf_bootup_distance%2Cn_bolts%2Chp_to_1b%2Csprint_speed&chart=false&x=player_age&y=player_age&r=no&chartType=beeswarm&sort=1&sortDir=desc&csv=true",
            "filename": "custom_batter_2025.csv"
        },
        {
            "url": "https://baseballsavant.mlb.com/leaderboard/custom?year=2025&type=pitcher&filter=&min=10&selections=player_age%2Cp_game%2Cp_formatted_ip%2Cpa%2Cab%2Chit%2Csingle%2Cdouble%2Ctriple%2Chome_run%2Cstrikeout%2Cwalk%2Ck_percent%2Cbb_percent%2Cbatting_avg%2Cslg_percent%2Con_base_percent%2Con_base_plus_slg%2Cisolated_power%2Cbabip%2Cp_earned_run%2Cp_run%2Cp_save%2Cp_blown_save%2Cp_out%2Cp_win%2Cp_loss%2Cp_wild_pitch%2Cp_balk%2Cp_shutout%2Cp_era%2Cp_opp_batting_avg%2Cp_opp_on_base_avg%2Cp_total_stolen_base%2Cp_pickoff_attempt_1b%2Cp_pickoff_attempt_2b%2Cp_pickoff_attempt_3b%2Cp_pickoff_1b%2Cp_pickoff_2b%2Cp_pickoff_3b%2Cp_lob%2Cp_rbi%2Cp_stolen_base_2b%2Cp_stolen_base_3b%2Cp_stolen_base_home%2Cp_quality_start%2Cp_walkoff%2Cp_run_support%2Cp_ab_scoring%2Cp_automatic_ball%2Cp_ball%2Cp_called_strike%2Cp_catcher_interf%2Cp_caught_stealing_2b%2Cp_caught_stealing_3b%2Cp_caught_stealing_home%2Cp_complete_game%2Cp_defensive_indiff%2Cp_foul%2Cp_foul_tip%2Cp_game_finished%2Cp_game_in_relief%2Cp_gnd_into_dp%2Cp_gnd_into_tp%2Cp_gnd_rule_double%2Cp_hit_by_pitch%2Cp_hit_fly%2Cp_hit_ground%2Cp_hit_line_drive%2Cp_hit_into_play%2Cp_hit_scoring%2Cp_hold%2Cp_intent_ball%2Cp_intent_walk%2Cp_missed_bunt%2Cp_out_fly%2Cp_out_ground%2Cp_out_line_drive%2Cp_passed_ball%2Cp_pickoff_error_1b%2Cp_pickoff_error_2b%2Cp_pickoff_error_3b%2Cp_pitchout%2Cp_relief_no_out%2Cp_sac_bunt%2Cp_sac_fly%2Cp_starting_p%2Cp_swinging_strike%2Cp_unearned_run%2Cp_total_ball%2Cp_total_bases%2Cp_total_caught_stealing%2Cp_total_pickoff%2Cp_total_pickoff_attempt%2Cp_total_pickoff_error%2Cp_total_pitches%2Cp_total_sacrifices%2Cp_total_strike%2Cp_total_swinging_strike%2Cp_inh_runner%2Cp_inh_runner_scored%2Cp_beq_runner%2Cp_beq_runner_scored%2Cp_reached_on_error%2Cxba%2Cxslg%2Cwoba%2Cxwoba%2Cxobp%2Cxiso%2Cwobacon%2Cxwobacon%2Cbacon%2Cxbacon%2Cxbadiff%2Cxslgdiff%2Cwobadiff%2Cavg_swing_speed%2Cfast_swing_rate%2Cblasts_contact%2Cblasts_swing%2Csquared_up_contact%2Csquared_up_swing%2Cavg_swing_length%2Cswords%2Cattack_angle%2Cattack_direction%2Cideal_angle_rate%2Cvertical_swing_path%2Cexit_velocity_avg%2Claunch_angle_avg%2Csweet_spot_percent%2Cbarrel%2Cbarrel_batted_rate%2Csolidcontact_percent%2Cflareburner_percent%2Cpoorlyunder_percent%2Cpoorlytopped_percent%2Cpoorlyweak_percent%2Chard_hit_percent%2Cavg_best_speed%2Cavg_hyper_speed%2Cz_swing_percent%2Cz_swing_miss_percent%2Coz_swing_percent%2Coz_swing_miss_percent%2Coz_contact_percent%2Cout_zone_swing_miss%2Cout_zone_swing%2Cout_zone_percent%2Cout_zone%2Cmeatball_swing_percent%2Cmeatball_percent%2Cpitch_count_offspeed%2Cpitch_count_fastball%2Cpitch_count_breaking%2Cpitch_count%2Ciz_contact_percent%2Cin_zone_swing_miss%2Cin_zone_swing%2Cin_zone_percent%2Cin_zone%2Cedge_percent%2Cedge%2Cwhiff_percent%2Cswing_percent%2Cpull_percent%2Cstraightaway_percent%2Copposite_percent%2Cbatted_ball%2Cf_strike_percent%2Cgroundballs_percent%2Cgroundballs%2Cflyballs_percent%2Cflyballs%2Clinedrives_percent%2Clinedrives%2Cpopups_percent%2Cpopups%2Cpitch_hand%2Cn%2Carm_angle%2Cn_ff_formatted%2Cff_avg_speed%2Cff_avg_spin%2Cff_avg_break_x%2Cff_avg_break_z%2Cff_avg_break_z_induced%2Cff_avg_break%2Cff_range_speed%2Cn_sl_formatted%2Csl_avg_speed%2Csl_avg_spin%2Csl_avg_break_x%2Csl_avg_break_z%2Csl_avg_break_z_induced%2Csl_avg_break%2Csl_range_speed%2Cn_ch_formatted%2Cch_avg_speed%2Cch_avg_spin%2Cch_avg_break_x%2Cch_avg_break_z%2Cch_avg_break_z_induced%2Cch_avg_break%2Cch_range_speed%2Cn_cu_formatted%2Ccu_avg_speed%2Ccu_avg_spin%2Ccu_avg_break_x%2Ccu_avg_break_z%2Ccu_avg_break_z_induced%2Ccu_avg_break%2Ccu_range_speed%2Cn_si_formatted%2Csi_avg_speed%2Csi_avg_spin%2Csi_avg_break_x%2Csi_avg_break_z%2Csi_avg_break_z_induced%2Csi_avg_break%2Csi_range_speed%2Cn_fc_formatted%2Cfc_avg_speed%2Cfc_avg_spin%2Cfc_avg_break_x%2Cfc_avg_break_z%2Cfc_avg_break_z_induced%2Cfc_avg_break%2Cfc_range_speed%2Cn_fs_formatted%2Cfs_avg_speed%2Cfs_avg_spin%2Cfs_avg_break_x%2Cfs_avg_break_z%2Cfs_avg_break_z_induced%2Cfs_avg_break%2Cfs_range_speed%2Cn_kn_formatted%2Ckn_avg_speed%2Ckn_avg_spin%2Ckn_avg_break_x%2Ckn_avg_break_z%2Ckn_avg_break_z_induced%2Ckn_avg_break%2Ckn_range_speed%2Cn_st_formatted%2Cst_avg_speed%2Cst_avg_spin%2Cst_avg_break_x%2Cst_avg_break_z%2Cst_avg_break_z_induced%2Cst_avg_break%2Cst_range_speed%2Cn_sv_formatted%2Csv_avg_speed%2Csv_avg_spin%2Csv_avg_break_x%2Csv_avg_break_z%2Csv_avg_break_z_induced%2Csv_avg_break%2Csv_range_speed%2Cn_fo_formatted%2Cfo_avg_speed%2Cfo_avg_spin%2Cfo_avg_break_x%2Cfo_avg_break_z%2Cfo_avg_break_z_induced%2Cfo_avg_break%2Cfo_range_speed%2Cn_sc_formatted%2Csc_avg_speed%2Csc_avg_spin%2Csc_avg_break_x%2Csc_avg_break_z%2Csc_avg_break_z_induced%2Csc_avg_break%2Csc_range_speed%2Cn_fastball_formatted%2Cfastball_avg_speed%2Cfastball_avg_spin%2Cfastball_avg_break_x%2Cfastball_avg_break_z%2Cfastball_avg_break_z_induced%2Cfastball_avg_break%2Cfastball_range_speed%2Cn_breaking_formatted%2Cbreaking_avg_speed%2Cbreaking_avg_spin%2Cbreaking_avg_break_x%2Cbreaking_avg_break_z%2Cbreaking_avg_break_z_induced%2Cbreaking_avg_break%2Cbreaking_range_speed%2Cn_offspeed_formatted%2Coffspeed_avg_speed%2Coffspeed_avg_spin%2Coffspeed_avg_break_x%2Coffspeed_avg_break_z%2Coffspeed_avg_break_z_induced%2Coffspeed_avg_break%2Coffspeed_range_speed&chart=false&x=player_age&y=player_age&r=no&chartType=beeswarm&sort=1&sortDir=desc&csv=true",
            "filename": "custom_pitcher_2025.csv"
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

if __name__ == "__main__":
    download_mlb_stats()