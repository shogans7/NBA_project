from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import datetime as dt
from oauth2client.service_account import ServiceAccountCredentials
import pytz

import scraper

local = True

try:
    chrome_options = webdriver.ChromeOptions()
    if not local:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument("start-maximized")
        ua = UserAgent()
        user_agent = ua.random
        chrome_options.add_argument(f'--user-agent={user_agent}')

    if local:
        # driver_service = Service(ChromeDriverManager().install())
        driver_service = Service('/Users/shanehogan/Downloads/chromedriver')
    else:
        driver_service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(service=driver_service, options=chrome_options)
    tz_params = {'timezoneId': 'US/Pacific'}
    driver.execute_cdp_cmd('Emulation.setTimezoneOverride', tz_params)

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    if local:
        json_file_pathname = "/Users/shanehogan/Downloads/crafty-haiku-361014-eb14babc812e.json"
    else:
        json_file_pathname = "/root/crafty-haiku-361014-eb14babc812e.json"

    credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file_pathname, scopes)

    tz = pytz.timezone('US/Pacific')
    current_date = dt.datetime.now(tz).strftime("%d-%m-%Y")
    current_time = dt.datetime.now(tz).strftime("%H:%M")
    print(current_date, current_time, "Pacific Standard Time")

    name = "Betfair"
    scraper.betfair_scraper(driver, current_date, current_time, name, credentials)

    driver.close()
    driver.quit()

except Exception as e:
    print(e)
    driver.close()
    driver.quit()