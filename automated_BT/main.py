from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import pandas as pd
import datetime as dt
from datetime import timedelta, datetime
import helper_functions
import rpy2
import rpy2.robjects as robjects
import numpy as np
from rpy2.robjects.packages import importr, data
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter
import math
import pytz
from fake_useragent import UserAgent
from oauth2client.service_account import ServiceAccountCredentials
import gspread


utils = importr('utils')
base = importr('base')
utils.chooseCRANmirror(ind=1)
utils.install_packages('BradleyTerry2')
BT2 = importr('BradleyTerry2')

local = True

tz = pytz.timezone('UTC')
today_ESPN_format = (dt.datetime.now(tz)).strftime("%Y%m%d")
today = (dt.datetime.now(tz)).strftime("%d-%m-%Y")
yesterday_ESPN_format = (dt.datetime.now(tz)-timedelta(days=1)).strftime("%Y%m%d")
yesterday = (dt.datetime.now(tz)-timedelta(days=1)).strftime("%d-%m-%Y")
match_date = yesterday_ESPN_format
fixtures_date = today_ESPN_format
print(match_date)

scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

chrome_options = webdriver.ChromeOptions()
if local:
    driver_service = Service('/Users/shanehogan/Downloads/chromedriver')
    file_path_in = "/Users/shanehogan/Desktop/Betting Project Data/NBA-Results--ALL.csv"
    json_file_pathname = "/Users/shanehogan/Downloads/crafty-haiku-361014-eb14babc812e.json"
    file_path_out = f"/Users/shanehogan/Desktop/Betting Project Data/BT-Probabilities/NBA-BT-Probabilities--{today}.csv"
else:
    driver_service = Service("/usr/bin/chromedriver")
    file_path_in = "~/NBA/data/NBA-Results--ALL.csv"
    json_file_pathname = "/root/crafty-haiku-361014-eb14babc812e.json"
    file_path_out = f"~/NBA/data/NBA-BT-Probabilities/NBA-BT-Probabilities--{today}.csv"
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument("start-maximized")


credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file_pathname, scopes)
file = gspread.authorize(credentials)
document = file.open("NBA_Results_ALL")

try:
    sheet = document.worksheet("DATA")
    final_df = helper_functions.clean_df_from_gsheets(pd.DataFrame(sheet.get_all_values()))
    print(final_df)
except Exception as e:
    print(e)


driver = webdriver.Chrome(service=driver_service, options=chrome_options)
tz_params = {'timezoneId': 'US/Pacific'}
driver.execute_cdp_cmd('Emulation.setTimezoneOverride', tz_params)
driver.get(f"https://www.espn.com/nba/scoreboard/_/date/{match_date}")
time.sleep(2)
# cookies_xpath = '//*[@id="onetrust-accept-btn-handler"]'
# accept = driver.find_element(by=By.XPATH, value=cookies_xpath)
# accept.click()
time.sleep(2)

df = helper_functions.parse_results(driver, match_date)
final_df = pd.concat([final_df, df], ignore_index = True)
cols_to_change = {"Match Date": int, "Away Score": int, "Home Score": int, "OT": int, "result": int}
final_df = final_df.astype(cols_to_change)
print(final_df)
final_df.to_csv(file_path_in, index = False)

driver.get(f"https://www.espn.com/nba/scoreboard/_/date/{fixtures_date}")
fixtures = helper_functions.parse_fixtures(driver, fixtures_date)
print(fixtures)

driver.close()
driver.quit()

with localconverter(robjects.default_converter + pandas2ri.converter):
    R_nba_results = robjects.conversion.py2rpy(final_df)

home_team_index = list(R_nba_results.colnames).index("Home Team")
home_team_factor = robjects.vectors.FactorVector(R_nba_results.rx2("Home Team"))
R_nba_results[home_team_index] = home_team_factor
home_team_df = robjects.vectors.DataFrame({"team":R_nba_results.rx2("Home Team"), "at_home":1})
R_nba_results[home_team_index] = home_team_df

away_team_index = list(R_nba_results.colnames).index("Away Team")
away_team_factor = robjects.vectors.FactorVector(R_nba_results.rx2("Away Team"))
R_nba_results[away_team_index] = away_team_factor
away_team_df = robjects.vectors.DataFrame({"team": R_nba_results.rx2("Away Team"), "at_home": 0})
R_nba_results[away_team_index] = away_team_df

formula = robjects.Formula("~team+at_home")
model = BT2.BTm(
    outcome=R_nba_results.rx2("result"),
    player1=R_nba_results.rx2("Home Team"), player2=R_nba_results.rx2("Away Team"),
    id="team", formula=formula, data=R_nba_results
)

BTabilities = BT2.BTabilities(model)

with localconverter(robjects.default_converter + pandas2ri.converter):
    vector = robjects.conversion.rpy2py(BTabilities)

abilities = [math.exp(elt)-1 for elt in vector[:, 0]]
teams_list = base.rownames(BTabilities)
df = pd.DataFrame([teams_list, abilities]).T
df.columns = ["Team", "Ability"]

alpha = model.rx2("coefficients")[-1]
BT_probs_dict = {}
for index, fixture in fixtures.iterrows():
    home_team = fixture["Home Team"]
    away_team = fixture["Away Team"]
    beta_home = df["Ability"][df["Team"] == home_team].values[0]
    beta_away = df["Ability"][df["Team"] == away_team].values[0]
    p_home = helper_functions.prob_i_beats_j(alpha, beta_home, beta_away)
    p_away = helper_functions.prob_i_beats_j(-alpha, beta_away, beta_home)
    BT_probs_dict[home_team] = round(p_home*100, 3)
    BT_probs_dict[away_team] = round(p_away*100, 3)

BT_probs_df = pd.DataFrame.from_dict([BT_probs_dict]).T
BT_probs_df.columns = ["Win Probability"]
BT_probs_df.to_csv(file_path_out, index=True)

print(BT_probs_df)

