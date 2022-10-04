import yagmail
import rpy2.robjects as robjects
import numpy as np
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter
import matplotlib.pyplot as plt
from rpy2.robjects.packages import importr, data

user = 't80246612@gmail.com'
app_password = 'zsjhapugfkthiiih'  # a token for gmail
to = 'hogans7@tcd.ie'
ffstream = importr('ffstream')


def decimal_odds_to_implied_prob(odds):
    return round(100 / (odds + 1), 2)


def is_arb(away, home):
    if away == "" or home == "":
        return False
    elif away == "0" or home == "":
        return False
    else:
        away = decimal_odds_to_implied_prob(float(away))
        home = decimal_odds_to_implied_prob(float(home))
        if away + home < 100:
            print("ARB DETECTED!!!!\n")
            return True
        else:
            print("No arbitrage\n")
            return False


def clean_df_from_gsheets(df):
    if not df.empty:
        headers = df.iloc[0].values
        df.columns = headers
        df.drop(index=0, axis=0, inplace=True)
    return df


def send_email(subject, content):
    with yagmail.SMTP(user, app_password) as yag:
        subject = subject
        content = content
        yag.send(to, subject, content)
        print('Sent email successfully')


def AFFchangepoints(df):
    changepoints = {}
    for index, row in df.iterrows():
        changepoint_series = row.copy()
        # changepoint_series = changepoint_series.drop(labels=["Team", 'Home/Away', 'Opposition'])
        changepoint_df = changepoint_series.to_frame().T
        changepoint_df = changepoint_df[changepoint_df.columns.drop(list(changepoint_df.filter(regex='Best bookie')))]
        changepoint_df = changepoint_df.replace({'': np.nan, 'nan': np.nan}, regex=True)

        if changepoint_df.isnull().values.any():
            print(row["Team"], "has missing values")
        #         IMPUTE HERE
        else:
            with localconverter(robjects.default_converter + pandas2ri.converter):
                r_row_vector = robjects.conversion.py2rpy(changepoint_df)
            stream = robjects.FloatVector([elt[0] for elt in r_row_vector])
            model = ffstream.detectAFFMean(stream, alpha=0.01, eta=0.01, BL=2, multiple=True)
            # name = row["Team"]
            name = index
            if str(model.rx2('tauhat')) == "integer(0)\n":
                print(name, ": No changepoints")
            else:
                print(name, ': Changepoints at', model.rx2('tauhat'))
                send_email(subject="Changepoints",
                           content=str(name) + ': Changepoints at ' + str(model.rx2('tauhat')))

            changepoints[name] = model.rx2('tauhat')

    return changepoints
