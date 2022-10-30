import time
import numpy as np
import gspread
import helper_functions
import pandas as pd
from selenium.webdriver.common.by import By


def betfair_scraper(driver, current_date, current_time, name, credentials):
    print(f'---- STARTING {name} ----')
    web = 'https://www.betfair.com/sport/basketball'
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

    button = driver.find_element(by=By.CSS_SELECTOR, value="[title=\"NBA\"]")
    button.click()

    time.sleep(5)
    box = driver.find_element(by=By.CLASS_NAME, value='section-list')
    box.location_once_scrolled_into_view


    #
    # # if not box.find_elements(by=By.CLASS_NAME,
    # #                          value='com-coupon-line-new-layout.betbutton-layout.avb-row.avb-table.last.market-avb.set-template.market-3-columns'):
    # #     print(f"Couldn't find any data at {name} website ")
    # #
    # # time.sleep(2)
    # # # .last.market-avb.set-template.market-3-columns
    for team in box.find_elements(by=By.CLASS_NAME, value='com-coupon-line-new-layout.betbutton-layout.avb-row.avb-table'):
        if team.text:
            txt = team.text.split('\n')
            print(txt)
            print(len(txt))
            if len(txt) == 13 or len(txt) == 14:
                if txt[0] == "In-Play":
                    print("Live match")
                    away_odds = helper_functions.odds_to_decimal(txt[-4])
                    home_odds = helper_functions.odds_to_decimal(txt[-5])
                    home = [txt[-1].split('(')[0].lstrip("@ ").rstrip(), "H", txt[-2].split('(')[0].rstrip(), str(home_odds), str(np.nan)]
                    home = pd.DataFrame(home).T
                    away = [txt[-2].split('(')[0].rstrip(), "A", txt[-1].split('(')[0].lstrip("@ ").rstrip(), str(away_odds), str(np.nan)]
                    away = pd.DataFrame(away).T
                    live_matches = pd.concat([live_matches, home, away], axis=0, ignore_index=True)
                else:
                    away_odds = helper_functions.odds_to_decimal(txt[-5])
                    home_odds = helper_functions.odds_to_decimal(txt[-4])
                    home = [txt[-1].split('(')[0].lstrip("@ ").rstrip(), "H", txt[-2].split('(')[0].rstrip(), str(home_odds)]
                    home = pd.DataFrame(home).T
                    away = [txt[-2].split('(')[0].rstrip(), "A", txt[-1].split('(')[0].lstrip("@ ").rstrip(), str(away_odds)]
                    away = pd.DataFrame(away).T
                    matches = pd.concat([matches, home, away], axis=0, ignore_index=True)
            else:
                print("Length of match data object in betfair was not as expected")
        elif not team.text:
            print('no more teams in featured matches to append')

    if not matches.empty:
        matches.columns = ["Team", "Home/Away", "Opposition", "Odds at " + str(current_time)]
        if join_pre_match:
            matches = pd.merge(pre_match_df, matches, on=["Team", "Home/Away", "Opposition"], how="left")
            # matches.drop_duplicates(subset=["Teams"], inplace=True, ignore_index=True)
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
            # live_matches.drop_duplicates(subset=["Teams"], inplace=True, ignore_index=True)
            live_matches = live_matches.fillna(
                '')  # Merge leaves some cells NA which the Google sheet JSON won't accept
            print(live_matches)
            worksheet = document.worksheet(current_date + "-Live")
            worksheet.update([live_matches.columns.values.tolist()] + live_matches.values.tolist())
        else:
            print(live_matches)
            worksheet = document.worksheet(current_date + "-Live")
            worksheet.update([live_matches.columns.values.tolist()] + live_matches.values.tolist())

    print(f'---- DONE {name} ----')