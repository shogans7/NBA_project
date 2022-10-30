import time
import numpy as np
import gspread
import helper_functions
import pandas as pd
from selenium.webdriver.common.by import By


def paddy_power_scraper(driver, current_date, current_time, name, credentials):
    print(f'---- STARTING {name} ----')
    web = 'https://www.paddypower.com/basketball'
    driver.get(web)

    time.sleep(15)
    driver.get_screenshot_as_file(f"{name}_{current_date}_{current_time}screenshot.png")
    cookies_xpath = '//*[@id="onetrust-accept-btn-handler"]'
    helper_functions.accept_cookies(driver, cookies_xpath)

    matches = pd.DataFrame()
    live_matches = pd.DataFrame()
    join_pre_match = True
    join_live_match = True

    file = gspread.authorize(credentials)
    document = file.open(f"{name}BasketballOdds")

    try:
        sheet = document.worksheet(current_date)
        pre_match_df = helper_functions.clean_df_from_gsheets(pd.DataFrame(sheet.get_all_values()))
        print(pre_match_df)
        if pre_match_df.empty:
            join_pre_match = False
    except Exception as e:
        document.add_worksheet(current_date, rows=30, cols=361)
        print(e)
        print("Sheet didn't exist yet, creating")
        join_pre_match = False

    try:
        sheet = document.worksheet(current_date + "-Live")
        live_match_df = helper_functions.clean_df_from_gsheets(pd.DataFrame(sheet.get_all_values()))
        print(live_match_df)
        if live_match_df.empty:
            join_live_match = False
    except Exception as e:
        document.add_worksheet(current_date + "-Live", rows=30, cols=361)
        print(e)
        print("Live sheet didn't exist yet, creating")
        join_live_match = False

    time.sleep(5)
    # OLD XPATH
    
    box = driver.find_element(by=By.CLASS_NAME, value='coupon-list')
    # box = driver.find_element(by=By.XPATH,
    #                           value='/html/body/div[1]/page-container/div/main/div/content-managed-page/div/div[2]/div/div[1]/coupon-card/div/abc-card/div/div/abc-card-content/div/avb-coupon/div')
    # box = driver.find_element(by=By.XPATH,
    #                           value='/html/body/div[1]/page-container/div/main/div/content-managed-page/div/div[2]/div/div[3]/coupon-card/div/abc-card/div/div/abc-card-content/div/avb-coupon/div')
    box.location_once_scrolled_into_view

    time.sleep(5)
    for team in box.find_elements(by=By.CLASS_NAME, value='avb-item__event-row'):
        if team.text:
            txt = team.text.split('\n')
            print(txt)
            if " " not in txt[0]:
                # implies match is live, is this a sufficient check?
                print("Live match")
                print(len(txt))
                # NB: Betting may be locked, hence check if returns length
                if len(txt) == 5:
                    print("BETTING FOR ONE OF THEM IS LOCKED")
                    print(txt)
                    if int(txt[2]) > int(txt[0]):
                        away_odds = helper_functions.odds_to_decimal(txt[4])
                        home_odds = np.nan
                    else:
                        home_odds = helper_functions.odds_to_decimal(txt[4])
                        away_odds = np.nan
                    # match = [txt[1] + " " + txt[3], str([away_odds, home_odds]), str([int(txt[0]), int(txt[2])])]
                    # data = pd.DataFrame(match).T
                    home = [txt[3], "H", txt[1].rstrip(" @"), str(home_odds), str(int(txt[2]))]
                    home = pd.DataFrame(home).T
                    away = [txt[1].rstrip(" @"), "A", txt[3], str(away_odds), str(int(txt[0]))]
                    away = pd.DataFrame(away).T
                    live_matches = pd.concat([live_matches, home, away], axis=0, ignore_index=True)
                # NOT SAFE, index can be out of bounds
                elif len(txt) > 4:
                    away_odds = helper_functions.odds_to_decimal(txt[4])
                    home_odds = helper_functions.odds_to_decimal(txt[5])
                    # match = [txt[1] + " " + txt[3], str([away_odds, home_odds]), str([int(txt[0]), int(txt[2])])]
                    # data = pd.DataFrame(match).T
                    home = [txt[3], "H", txt[1].rstrip(" @"), str(home_odds), str(int(txt[2]))]
                    home = pd.DataFrame(home).T
                    away = [txt[1].rstrip(" @"), "A", txt[3], str(away_odds), str(int(txt[0]))]
                    away = pd.DataFrame(away).T
                    live_matches = pd.concat([live_matches, home, away], axis=0, ignore_index=True)
                else:
                    print("Betting is locked")

            else:
                away_odds = helper_functions.odds_to_decimal(txt[2])
                home_odds = helper_functions.odds_to_decimal(txt[3])
                # match = [txt[0] + " " + txt[1], str([away_odds, home_odds])]
                # data = pd.DataFrame(match).T
                home = [txt[1], "H", txt[0].rstrip(" @"), str(home_odds)]
                home = pd.DataFrame(home).T
                away = [txt[0].rstrip(" @"), "A", txt[1], str(away_odds)]
                away = pd.DataFrame(away).T
                matches = pd.concat([matches, home, away], axis=0, ignore_index=True)
        elif not team.text:
            print('no more teams in featured matches to append')

    if not matches.empty:
        matches.columns = ["Team", "Home/Away", "Opposition", "Odds at " + str(current_time)]
        if join_pre_match:
            matches = pd.merge(pre_match_df, matches, on=["Team", "Home/Away", "Opposition"], how="left")
            matches.drop_duplicates(subset=["Team"], inplace=True, ignore_index=True)
            matches = matches.fillna('')  # Merge leaves some cells NA which the Google sheet JSON won't accept
            print(matches)
            worksheet = document.worksheet(current_date)
            worksheet.update([matches.columns.values.tolist()] + matches.values.tolist())
        else:
            print(matches)
            worksheet = document.worksheet(current_date)
            worksheet.update([matches.columns.values.tolist()] + matches.values.tolist())

    if not live_matches.empty:
        print("\n ___LIVE____ ")
        live_matches.columns = ["Team", "Home/Away", "Opposition", "Odds at " + str(current_time), "Score at " + str(current_time)]
        if join_live_match:
            live_matches = pd.merge(live_match_df, live_matches, on=["Team", "Home/Away", "Opposition"], how="outer")
            # live_matches.drop_duplicates(subset=["Team"], inplace=True, ignore_index=True)
            live_matches = live_matches.fillna('')  # Merge leaves some cells NA which the Google sheet JSON won't accept
            print(live_matches)
            worksheet = document.worksheet(current_date + "-Live")
            worksheet.update([live_matches.columns.values.tolist()] + live_matches.values.tolist())
        else:
            print(live_matches)
            worksheet = document.worksheet(current_date + "-Live")
            worksheet.update([live_matches.columns.values.tolist()] + live_matches.values.tolist())

    print(matches)
    print(live_matches)

    print(f'---- DONE {name} ----')
