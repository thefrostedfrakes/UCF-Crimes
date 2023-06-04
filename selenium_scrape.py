from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup

CHROME_DRIVER_PATH = 'C:/Users/<XXXX>/documents/chromedriver_win32/chromedriver.exe'

# Uses Selenium to get the top result in 'Most Popular Places at this Location' subsection
# Takes a while tho
# Enter the path to your chromedriver.exe file in the service variable
# HELPER FUNCTION FOR REPLACE_ADDRESS()
def selenium_scrape(expanded_address: str):
    TARGET_CLASS = 'fpqsoc'

    # prepare a google search url for a request
    url = 'https://www.google.com/search?q=' + expanded_address.replace(' ', '+')

    # Set up Selenium webdriver
    options = Options()
    options.add_argument('--headless')
    service = Service(CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    # Get the page and wait for the js to run
    driver.get(url)
    wait = WebDriverWait(driver, 8)
    try:
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, TARGET_CLASS)))
    except:
        return None

    # Get the new HTML after the js has run
    html = driver.page_source
    driver.quit()

    # Now we can parse the HTML with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    results = soup.find_all(class_=TARGET_CLASS)

    return results[0].text