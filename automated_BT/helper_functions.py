import pandas as pd
from selenium.webdriver.common.by import By
import math
import numpy as np


def parse_results(driver, match_date):
    df = pd.DataFrame()
    for box in driver.find_elements(by=By.CLASS_NAME, value='Card.gameModules'):
        box.location_once_scrolled_into_view
        for team in box.find_elements(by=By.CLASS_NAME, value='Scoreboard.bg-clr-white.flex.flex-auto.justify-between'):
            if team.text:
                txt = team.text.split('\n')
                if txt[0] == 'FINAL':
                    if txt[6] == "36ers" or txt[6] == "Maccabi":
                        print("Not an NBA team")
                    else:
                        match_list = [match_date, txt[6], txt[13], int(txt[12]), int(txt[19]), 0]
                        match = pd.DataFrame(match_list).T
                        match.columns = ["Match Date","Away Team", "Home Team", "Away Score", "Home Score", "OT"]
                        df = pd.concat([df, match], ignore_index=True)
                elif txt[0] == 'FINAL/OT' or txt[0] == 'FINAL/2OT' or txt[0] == 'FINAL/3OT' or txt[0] == 'FINAL/4OT':
                    match_list = [match_date, txt[7], txt[15], int(txt[14]), int(txt[22]), 1]
                    match = pd.DataFrame(match_list).T
                    match.columns = ["Match Date","Away Team", "Home Team", "Away Score", "Home Score", "OT"]
                    df = pd.concat([df, match], ignore_index = True)
                elif txt[0] == 'POSTPONED':
                    print(txt[1], "@", txt[3], txt[0])
                else:
                    raise Exception("UNSEEN FORMAT PARSING MATCH DATA", match_date)

    df["result"] = np.where(df['Home Score'] > df["Away Score"], 1, 0)
    return df


def parse_fixtures(driver, fixtures_date):
    df = pd.DataFrame()
    for box in driver.find_elements(by=By.CLASS_NAME, value='Card.gameModules'):
        box.location_once_scrolled_into_view
        for team in box.find_elements(by=By.CLASS_NAME, value='Scoreboard.bg-clr-white.flex.flex-auto.justify-between'):
            if team.text:
                txt = team.text.split('\n')
                channels = ['ESPN', 'TNT', 'NBA TV', 'ABC', 'ESPN2']
                if txt[1] in channels:
                    if txt[2] in channels:
                        match_list = [fixtures_date, txt[3], txt[5]]
                        match = pd.DataFrame(match_list).T
                        match.columns = ["Match Date", "Away Team", "Home Team"]
                        df = pd.concat([df, match], ignore_index=True)
                    else:
                        match_list = [fixtures_date, txt[2], txt[4]]
                        match = pd.DataFrame(match_list).T
                        match.columns = ["Match Date", "Away Team", "Home Team"]
                        df = pd.concat([df, match], ignore_index=True)
                else:
                    match_list = [fixtures_date, txt[1], txt[3]]
                    match = pd.DataFrame(match_list).T
                    match.columns = ["Match Date", "Away Team", "Home Team"]
                    df = pd.concat([df, match], ignore_index=True)

    return df


def prob_i_beats_j(alpha, beta_home, beta_away):
    return (math.exp(alpha+beta_home-beta_away))/(1+math.exp(alpha+beta_home-beta_away))


def clean_df_from_gsheets(df):
    if not df.empty:
        headers = df.iloc[0].values
        df.columns = headers
        df.drop(index=0, axis=0, inplace=True)
    return df


