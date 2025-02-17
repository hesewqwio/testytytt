import logging
from time import sleep
from random import randint
from src.browser import Browser

class Searches:
    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver

    def performSearch(self, url: str, duration: int) -> None:
        self.browser.visitURL(url, duration)
        logging.info(f"Performed search on {url} for {duration} minutes.")
        sleep(randint(10, 15))
