from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import datetime as dt
from oauth2client.service_account import ServiceAccountCredentials
import pytz
import stem.process
import requests
import json
import random

import scraper

local = True

try:

    SOCKS_PORT = 9050
    if local:
        TOR_PATH = '/Applications/Tor Browser.app/Contents/MacOS/Tor/tor.real'
        geoip_path = '/Applications/Tor Browser.app/Contents/Resources/TorBrowser/Tor/geoip'
        geoipv6_path = '/Applications/Tor Browser.app/Contents/Resources/TorBrowser/Tor/geoip6'
    else:
        TOR_PATH = '/./usr/bin/tor'
        geoip_path = '~/geoip'
        geoipv6_path = '~/geoip6'

    # DICTIONARY of countries where your desired website is unrestricted, and relevant tor code
    # FOUND at https://techearl.com/security/torrc
    # NB: some countries do not have enough exit nodes to work properly
    unrestricted_countries_dict = {
        # "Czechia": "{cz}",
        # "Finland": "{fi}",
        # "Japan": "{jp}",
        # "Norway": "{no}",
        # "Sweden": "{se}",
        # "Switzerland": "{ch}",
        "United States": "{us}",
        # "United Kingdom": "{gb}"
    }

    selected_country = random.choice(list(unrestricted_countries_dict.keys()))
    print("Selected exit country is", selected_country)

    tor_process = stem.process.launch_tor_with_config(
        config={
            'SocksPort': str(SOCKS_PORT),
            'ExitNodes': f'{unrestricted_countries_dict[selected_country]}',
            'StrictNodes': '1',
            'CookieAuthentication': '1',
            'MaxCircuitDirtiness': '60',
            'GeoIPFile': geoip_path,
            'GeoIPv6File': geoipv6_path
        },
        # init_msg_handler=lambda line: print(line) if re.search('Bootstrapped', line) else False,
        tor_cmd=TOR_PATH
    )

    PROXIES = {
        'http': 'socks5://127.0.0.1:9050',
        'https': 'socks5://127.0.0.1:9050'
    }

    # CHECKS where our IP is from, and throws an error if we've been served an incorrect exit node
    response = requests.get("http://ip-api.com/json/", proxies=PROXIES)
    result = json.loads(response.content)
    print('TOR IP [%s]: %s %s' % (dt.datetime.now().strftime("%d-%m-%Y %H:%M:%S"), result["query"], result["country"]))
    if result["country"] == selected_country:
        print("Valid exit node")
    else:
        raise Exception("Incorrect exit node")

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
        PROXY = PROXIES['http']
        chrome_options.add_argument('--proxy-server=%s' % PROXY)
        chrome_options.add_argument("--lang=en-US")
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
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

    name = "888"
    scraper.bet888_scraper(driver, current_date, current_time, name, credentials)

    tor_process.kill()
    driver.close()
    driver.quit()

except Exception as e:
    print(e)
    tor_process.kill()
    driver.close()
    driver.quit()

