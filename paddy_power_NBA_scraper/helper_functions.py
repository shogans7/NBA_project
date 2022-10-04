import numpy as np
import selenium.common.exceptions
from selenium.webdriver.common.by import By

nba_teams_list = ["Chicago Bulls"]


def odds_to_implied_prob(odds):
    # if type(odds) == "String":
    if odds == "EVS" or odds == "SUSP" or odds == "N/A":
        return np.nan
    else:
        odds = odds.split("/")
        odds = [int(o) for o in odds]
        return round(odds[1] / (odds[0] + odds[1]), 3)
    # elif type(odds) == int:
    #     return 1/(1+odds)


def odds_to_decimal(odds):
    if odds == "EVS" or odds == "SUSP" or odds == "N/A":
        return np.nan
    else:
        odds = odds.split("/")
        odds = [int(o) for o in odds]
        return round(odds[0] / odds[1], 3)


def accept_cookies(driver, cookies_xpath):
    try:
        accept = driver.find_element(by=By.XPATH, value=cookies_xpath)
        accept.click()
    except (selenium.common.exceptions.NoSuchElementException, selenium.common.exceptions.TimeoutException) as e:
        # print(e)
        print("No cookies button")


def clean_df_from_gsheets(df):
    if not df.empty:
        headers = df.iloc[0].values
        df.columns = headers
        df.drop(index=0, axis=0, inplace=True)
    return df
