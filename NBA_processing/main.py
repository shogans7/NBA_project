import pandas as pd
import datetime
import numpy as np
import random
from datetime import timedelta
import helper_functions
import matplotlib.pyplot as plt
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np
from rpy2.robjects.packages import importr, data


utils = importr('utils')
base = importr('base')
utils.chooseCRANmirror(ind=1)
utils.install_packages('ffstream')
ffstream = importr('ffstream')


# SETUP
names = ["PaddyPower", "Betfair"]
current_date = datetime.datetime.now()
yesterday = (current_date - timedelta(days=1)).strftime("%d-%m-%Y")
today = current_date.strftime("%d-%m-%Y")

date = yesterday

scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

json_file_pathname = "/Users/shanehogan/Downloads/crafty-haiku-361014-eb14babc812e.json"
credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file_pathname, scopes)

odds = {}
live_odds = {}

for name in names:
    file = gspread.authorize(credentials)
    document = file.open(f"{name}BaseballOdds")

    try:
        sheet = document.worksheet(date)
        pre_match_df = helper_functions.clean_df_from_gsheets(pd.DataFrame(sheet.get_all_values()))
    except Exception as e:
        print(e)
        print("Pre match sheet didn't exist yet", date)

    try:
        sheet = document.worksheet(date + "-Live")
        live_match_df = helper_functions.clean_df_from_gsheets(pd.DataFrame(sheet.get_all_values()))
    except Exception as e:
        print(e)
        print("Live sheet didn't exist yet", date)

    odds[name] = pre_match_df
    live_odds[name] = live_match_df

file = gspread.authorize(credentials)
document = file.open("BaseballBestOdds")

join_pre_match = True
join_live_match = True

try:
    sheet = document.worksheet(date)
    prev_best_odds_df = helper_functions.clean_df_from_gsheets(pd.DataFrame(sheet.get_all_values()))
    if prev_best_odds_df.empty:
        join_pre_match = False
except Exception as e:
    document.add_worksheet(date, rows=30, cols=361)
    print(e)
    print("Sheet didn't exist yet, creating")
    join_pre_match = False

try:
    sheet = document.worksheet(date + "-Live")
    prev_live_best_odds_df = helper_functions.clean_df_from_gsheets(pd.DataFrame(sheet.get_all_values()))
    if prev_live_best_odds_df.empty:
        join_live_match = False
except Exception as e:
    document.add_worksheet(date + "-Live", rows=30, cols=361)
    print(e)
    print("Live sheet didn't exist yet, creating")
    join_live_match = False

# _________________________________________


# GET BEST ODDS FOR MATCHES YET TO START
best_odds = {}
final_time = 0
for bookie in odds:
    last_read_time = odds[bookie].columns[-1].lstrip("Odds at ")
    last_read_time = last_read_time.replace(":", ".")
    if float(last_read_time) > float(final_time):
        final_time = last_read_time
    for index, row in odds[bookie].iterrows():
        best_odds[row["Team"]] = 0

final_time = final_time.replace(".", ":")
bookie_dict_pre = {}
for bookie in odds:
    for index, row in odds[bookie].iterrows():
        try:
            if float(row["Odds at " + final_time]) > float(best_odds[row["Team"]]):
                best_odds[row["Team"]] = row.iloc[-1]
                bookie_dict_pre[row["Team"]] = bookie
            elif float(row["Odds at " + final_time]) == float(best_odds[row["Team"]]):
                bookie_dict_pre[row["Team"]] = bookie_dict_pre[row["Team"]] + "/" + bookie
        except (ValueError, KeyError) as e:
            print("Bookie has no odds at the most recent scrape:", bookie)

bookie_df_pre = pd.DataFrame.from_dict([bookie_dict_pre]).T
bookie_df_pre.columns = ["Best bookie at " + final_time]
bookie_df_pre

best_odds_df = pd.DataFrame.from_dict([best_odds]).T
best_odds_df.columns = ["Odds at " + final_time]
best_odds_df

best_odds_df = best_odds_df.join(bookie_df_pre)

home = True
prev_odds = 0
prev_team = ""
for index, row in best_odds_df.iterrows():
    if home:
        prev_odds = row.values[0]
        prev_team = index
        prev_bookie = row.values[1]
        home = False
    #         if decimal_odds_to_implied_prob(float(row.values[0])) < model_probs.loc[index].values[0]:
    #             print("Discrepancy in odds with modelled probability", index, decimal_odds_to_implied_prob(float(row.values[0])), "<", model_probs.loc[index].values[0])

    elif not home:
        away_odds = row.values[0]
        home_odds = prev_odds
        print("Bookie is", row.values[1])
        print(index, "@", prev_team)
        print(away_odds, home_odds)
        arb = helper_functions.is_arb(away_odds, home_odds)
        if arb:
            line1 = index + " @ " + prev_team
            line2 = "(HOME) " + prev_team + " at " + str(prev_odds) + " on " + prev_bookie
            line3 = "(AWAY) " + index + " at " + str(row.values[0]) + " on " + row.values[1]
            helper_functions.send_email(subject="Arbitrage", content=[line1, line2, line3])
        home = True
#         if decimal_odds_to_implied_prob(float(row.values[0])) < model_probs.loc[index].values[0]:
#             print("Discrepancy in odds with modelled probability", index, decimal_odds_to_implied_prob(float(row.values[0])), "<", model_probs.loc[index].values[0])


# _________________________________________


# GET BEST ODDS FOR LIVE MATCHES
live_best_odds = {}
live_final_time = 0
for bookie in live_odds:
    if not live_odds[bookie].empty:
        last_read_time = live_odds[bookie].columns[-2].lstrip("Odds at ")
        last_read_time = last_read_time.replace(":", ".")
        if float(last_read_time) > float(live_final_time):
            live_final_time = last_read_time
        for index, row in live_odds[bookie].iterrows():
            # INITIALISE DICT
            live_best_odds[row["Team"]] = 0

if not live_final_time == 0:
    live_final_time = live_final_time.replace(".", ":")
    bookie_dict_live = {}
    for bookie in live_odds:
        if not live_odds[bookie].empty:
            for index, row in live_odds[bookie].iterrows():
                try:
                    if float(row["Odds at " + live_final_time]) > float(live_best_odds[row["Team"]]):
                        live_best_odds[row["Team"]] = row.iloc[-2]
                        bookie_dict_live[row["Team"]] = bookie
                    elif float(row["Odds at " + live_final_time]) == float(live_best_odds[row["Team"]]):
                        bookie_dict_live[row["Team"]] = bookie_dict_live[row["Team"]] + "/" + bookie
                except (ValueError, KeyError) as e:
                    print("Bookie has no odds at the most recent scrape:", bookie)

    bookie_df_live = pd.DataFrame.from_dict([bookie_dict_live]).T
    bookie_df_live.columns = ["Best bookie at " + live_final_time]
    bookie_df_live

    live_best_odds_df = pd.DataFrame.from_dict([live_best_odds]).T
    live_best_odds_df.columns = ["Odds at " + live_final_time]
    live_best_odds_df

    live_best_odds_df = live_best_odds_df.join(bookie_df_live)

    home = True
    prev_odds = 0
    prev_team = ""
    for index, row in live_best_odds_df.iterrows():
        if home:
            prev_odds = row.values[0]
            prev_team = index
            home = False

        elif not home:
            away_odds = row.values[0]
            home_odds = prev_odds
            print("Bookie is", row.values[1])
            print(index, "@", prev_team)
            print(away_odds, home_odds)
            helper_functions.is_arb(away_odds, home_odds)
            home = True


print(live_best_odds_df)
cp = helper_functions.AFFchangepoints(live_best_odds_df)
print(cp)

# _________________________________________


# SAVE BEST ODDS TO SHEET

best_odds_df = best_odds_df.replace({0: '', 'nan': '', 'Nan': '', np.nan: '', pd.NA: ''}, regex=True)
best_odds_df.reset_index(inplace=True)
best_odds_df = best_odds_df.rename(columns={'index': 'Team'})

if join_pre_match:
    #     if columns differ else nothing
    best_odds_df = pd.merge(prev_best_odds_df, best_odds_df, on=["Team"], how="left")
    #     live_best_odds_df.drop_duplicates(subset=["Teams"], inplace=True, ignore_index=True)
    best_odds_df = best_odds_df.fillna('')  # Merge leaves some cells NA which the Google sheet JSON won't accept
    worksheet = document.worksheet(date)
    worksheet.update([best_odds_df.columns.values.tolist()] + best_odds_df.values.tolist())
else:
    worksheet = document.worksheet(date)
    temp = odds[name].loc[:, ["Team", "Home/Away", "Opposition"]].copy()
    best_odds_df = pd.merge(temp, best_odds_df, on=["Team"], how='left')
    worksheet.update([best_odds_df.columns.values.tolist()] + best_odds_df.values.tolist())

if not live_final_time == 0:
    live_best_odds_df = live_best_odds_df.replace({0: '', 'nan': '', 'Nan': '', np.nan: '', pd.NA: ''}, regex=True)
    live_best_odds_df.reset_index(inplace=True)
    live_best_odds_df = live_best_odds_df.rename(columns={'index': 'Team'})

    if join_live_match:
        #     if columns differ else nothing
        live_best_odds_df = pd.merge(prev_live_best_odds_df, live_best_odds_df, on=["Team"], how="outer")
        #     live_best_odds_df.drop_duplicates(subset=["Teams"], inplace=True, ignore_index=True)
        live_best_odds_df = live_best_odds_df.fillna(
            '')  # Merge leaves some cells NA which the Google sheet JSON won't accept
        worksheet = document.worksheet(date + "-Live")
        worksheet.update([live_best_odds_df.columns.values.tolist()] + live_best_odds_df.values.tolist())
    else:
        worksheet = document.worksheet(date + "-Live")
        temp = live_odds[name].loc[:, ["Team", "Home/Away", "Opposition"]].copy()
        live_best_odds_df = pd.merge(temp, live_best_odds_df, on=["Team"], how='left')
        worksheet.update([live_best_odds_df.columns.values.tolist()] + live_best_odds_df.values.tolist())

