import logging
import logging.config
import logging.handlers as handlers
import sys
import traceback
from datetime import datetime

from src import Browser, Searches
from src.utils import CONFIG, sendNotification, getProjectRoot
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from time import sleep

def setupLogging():
    _format = CONFIG['logging']['format']
    _level = CONFIG['logging']['level']
    terminalHandler = logging.StreamHandler(sys.stdout)
    terminalHandler.setFormatter(logging.Formatter(_format))

    logs_directory = getProjectRoot() / "logs"
    logs_directory.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": True,
        }
    )
    logging.basicConfig(
        level=logging.getLevelName(_level.upper()),
        format=_format,
        handlers=[
            handlers.TimedRotatingFileHandler(
                logs_directory / "activity.log",
                when="midnight",
                interval=1,
                backupCount=2,
                encoding="utf-8",
            ),
            terminalHandler,
        ],
    )

def perform_searches(mobile):
    with Browser(mobile=mobile) as browser:
        if CONFIG['youtube']['enabled'] and "youtube.com" in CONFIG['url']:
            browser.webdriver.get("https://www.youtube.com")
            browser.load_cookies(service_name="youtube")
            browser.webdriver.refresh()
            sleep(5)  # Wait for the page to load with cookies

        searches = Searches(browser=browser)
        searches.performSearch(CONFIG['url'], CONFIG['duration'])

        if CONFIG['youtube']['enabled'] and "youtube.com" in CONFIG['url']:
            watch_youtube_video(browser, CONFIG['duration'])
            browser.save_cookies(service_name="youtube")

def watch_youtube_video(browser, duration):
    wait = WebDriverWait(browser.webdriver, 10)
    play_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Play (k)']")))
    play_button.click()
    logging.info(f"Watching YouTube video for {duration} minutes.")

    end_time = time.time() + duration * 60  # Calculate the end time
    while time.time() < end_time:
        try:
            # Detect and click the "Skip Ad" button if it appears
            ad_skip_button = browser.webdriver.find_element(By.CLASS_NAME, "ytp-ad-skip-button")
            if ad_skip_button.is_displayed():
                ad_skip_button.click()
                logging.info("Skipped an ad.")
        except:
            pass
        sleep(5)  # Check for the skip button every 5 seconds

    logging.info("Finished watching the video.")

def main():
    setupLogging()

    search_type = CONFIG['search']['type']

    try:
        if search_type in ("desktop", "both"):
            logging.info("Performing desktop searches...")
            perform_searches(mobile=False)  # Perform desktop searches

        if search_type in ("mobile", "both"):
            logging.info("Performing mobile searches...")
            perform_searches(mobile=True)  # Perform mobile searches

    except Exception as e:
        logging.exception("")
        sendNotification("⚠️ Error occurred, please check the log", traceback.format_exc(), e)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception("")
        sendNotification("⚠️ Error occurred, please check the log", traceback.format_exc(), e)
        exit(1)
