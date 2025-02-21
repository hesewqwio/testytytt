import dbm.dumb
import json
import logging
import shelve
from datetime import date, timedelta
from enum import Enum, auto
from itertools import cycle
from random import random, randint, shuffle
from time import sleep
from typing import Final

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException
import contextlib
from selenium.webdriver.common.keys import Keys

from src.browser import Browser
from src.utils import CONFIG, makeRequestsSession, getProjectRoot


class RetriesStrategy(Enum):
    """
    method to use when retrying
    """

    EXPONENTIAL = auto()
    """
    an exponentially increasing `base_delay_in_seconds` between attempts
    """
    CONSTANT = auto()
    """
    the default; a constant `base_delay_in_seconds` between attempts
    """


class Searches:
    maxRetries: Final[int] = CONFIG.get("retries").get("max")
    """
    the max amount of retries to attempt
    """
    baseDelay: Final[float] = CONFIG.get("retries").get("base_delay_in_seconds")
    """
    how many seconds to delay
    """
    # retriesStrategy = Final[  # todo Figure why doesn't work with equality below
    retriesStrategy = RetriesStrategy[CONFIG.get("retries").get("strategy")]

    def __init__(self, browser: Browser):
        self.browser = browser
        self.webdriver = browser.webdriver

        dumbDbm = dbm.dumb.open((getProjectRoot() / "google_trends").__str__())
        self.googleTrendsShelf: shelve.Shelf = shelve.Shelf(dumbDbm)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.googleTrendsShelf.__exit__(None, None, None)

    def getGoogleTrends(self, wordsCount: int) -> list[str]:
        # Function to retrieve Google Trends search terms
        searchTerms: list[str] = []
        i = 0
        session = makeRequestsSession()
        while len(searchTerms) < wordsCount:
            i += 1
            # Fetching daily trends from Google Trends API
            r = session.get(
                f"https://trends.google.com/trends/api/dailytrends?hl={self.browser.localeLang}"
                f'&ed={(date.today() - timedelta(days=i)).strftime("%Y%m%d")}&geo={self.browser.localeGeo}&ns=15'
            )
            assert (
                r.status_code == requests.codes.ok
            ), "Adjust retry config in src.utils.Utils.makeRequestsSession"
            trends = json.loads(r.text[6:])
            for topic in trends["default"]["trendingSearchesDays"][0][
                "trendingSearches"
            ]:
                searchTerms.append(topic["title"]["query"].lower())
                searchTerms.extend(
                    relatedTopic["query"].lower()
                    for relatedTopic in topic["relatedQueries"]
                )
            searchTerms = list(set(searchTerms))
        del searchTerms[wordsCount : (len(searchTerms) + 1)]
        return searchTerms

    def getRelatedTerms(self, term: str) -> list[str]:
        # Function to retrieve related terms from Bing API
        relatedTerms: list[str] = (
            makeRequestsSession()
            .get(
                f"https://api.bing.com/osjson.aspx?query={term}",
                headers={"User-agent": self.browser.userAgent},
            )
            .json()[1]
        )
        uniqueTerms = list(dict.fromkeys(relatedTerms))  # Remove duplicates
        uniqueTerms = [t for t in uniqueTerms if t.lower() != term.lower()]  # Exclude exact term
        return uniqueTerms

    def bingSearches(self, searchRelatedTerms: bool = False, relatedTermsCount: int = 0) -> None:
        logging.info(f"[BING] Starting {self.browser.browserType.capitalize()} Edge Bing searches...")

        self.browser.utils.goToSearch()

        desktopAndMobileRemaining = self.browser.getRemainingSearches(desktopAndMobile=True)
        remainingSearches = desktopAndMobileRemaining.getTotal()
        searchCount = 0
        while searchCount < remainingSearches:
            logging.info(f"[BING] {searchCount + 1}/{remainingSearches}")
            searchCount = self.bingSearch(searchRelatedTerms, relatedTermsCount, searchCount)
            if searchCount >= remainingSearches:
                break

            if desktopAndMobileRemaining.getTotal() > len(self.googleTrendsShelf):
                # self.googleTrendsShelf.clear()  # Maybe needed?
                logging.debug(
                    f"google_trends before load = {list(self.googleTrendsShelf.items())}"
                )
                trends = self.getGoogleTrends(desktopAndMobileRemaining.getTotal())
                shuffle(trends)
                for trend in trends:
                    self.googleTrendsShelf[trend] = None
                logging.debug(
                    f"google_trends after load = {list(self.googleTrendsShelf.items())}"
                )

            if searchRelatedTerms:
                rootTerm = list(self.googleTrendsShelf.keys())[0]  # Adjusted from 1 to 0
                terms = self.getRelatedTerms(rootTerm)
                uniqueTerms = list(dict.fromkeys(terms))
                uniqueTerms = [t for t in uniqueTerms if t.lower() != rootTerm.lower()]
                for i, _ in enumerate(uniqueTerms[:relatedTermsCount]):
                    searchCount = self.bingSearch(searchRelatedTerms, relatedTermsCount, searchCount)
                    if searchCount >= remainingSearches:
                        break

            self.bingSearch()
            del self.googleTrendsShelf[list(self.googleTrendsShelf.keys())[0]]
            sleep(randint(10, 15))  # Short delay added here

        logging.info(f"[BING] Finished {self.browser.browserType.capitalize()} Edge Bing searches!")

    def manually_enter_text(self, searchbar, term: str, min_delay: float = 0.2, max_delay: float = 0.7):
        for char in term:
            searchbar.send_keys(char)
            sleep(random() * (max_delay - min_delay) + min_delay)  # Random delay between keystrokes to mimic manual typing

    def bingSearch(self, searchRelatedTerms: bool = False, relatedTermsCount: int = 0, searchCount: int = 0) -> int:
        if not self.googleTrendsShelf:
            logging.error("googleTrendsShelf is empty, unable to proceed with search.")
            return searchCount

        pointsBefore = self.browser.utils.getAccountPoints()
        rootTerm = list(self.googleTrendsShelf.keys())[0]  # Adjusted from 1 to 0 for consistency
        terms = self.getRelatedTerms(rootTerm)
        uniqueTerms = list(dict.fromkeys(terms))  # Remove duplicates
        uniqueTerms = [t for t in uniqueTerms if t.lower() != rootTerm.lower()]  # Exclude exact root term
        logging.debug(f"rootTerm={rootTerm}")
        logging.debug(f"uniqueTerms={uniqueTerms}")

        if searchRelatedTerms:
            terms = [rootTerm] + uniqueTerms[:relatedTermsCount]  # Dynamically handle related terms count
        else:
            terms = [rootTerm]

        logging.debug(f"terms={terms}")

        searchbar = self.browser.utils.waitUntilClickable(By.ID, "sb_form_q", timeToWait=40)
        termsCycle: cycle[str] = cycle(terms)  # Define the terms cycle here
        for _ in range(3):
            searchbar.clear()
            term = next(termsCycle)
            logging.debug(f"term={term}")
            self.manually_enter_text(searchbar, term, min_delay=0.2, max_delay=0.7)  # Use the manual typing function
            with contextlib.suppress(TimeoutException):
                WebDriverWait(self.webdriver, 40).until(
                    expected_conditions.text_to_be_present_in_element_value((By.ID, "sb_form_q"), term)
                )
                break
            logging.debug("error send_keys")
        else:
            raise TimeoutException

        searchbar.submit()
        pointsAfter = self.browser.utils.getAccountPoints()
        searchCount += 1  # Increment the search count regardless of outcome
        logging.info(f"[BING] {searchCount} searches completed")

        if pointsBefore < pointsAfter:
            del self.googleTrendsShelf[rootTerm]
        else:
            logging.debug("Moving passedInTerm to end of list")
            del self.googleTrendsShelf[rootTerm]
            self.googleTrendsShelf[rootTerm] = None

        # Wait for 15 seconds before scrolling and opening the first result
        sleep(15)

        # Scroll through the search results page to mimic human behavior
        for _ in range(15):
            self.webdriver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
            sleep(1)

        # Open the first search result
        first_result = WebDriverWait(self.webdriver, 10).until(
            expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, "h2 a"))
        )
        first_result.click()

        # Stay on the first search result page for 120 seconds
        sleep(120)

        # Ensure delay after each root term search
        sleep(randint(220, 280))

        if searchRelatedTerms:
            logging.debug("Starting additional searches for related terms")
            for i, related_term in enumerate(uniqueTerms):
                if i >= relatedTermsCount:
                    break
                try:
                    searchbar = self.browser.utils.waitUntilClickable(By.ID, "sb_form_q", timeToWait=40)
                    searchbar.clear()
                    logging.debug(f"related term={related_term}")
                    self.manually_enter_text(searchbar, related_term, min_delay=0.2, max_delay=0.7)  # Use the manual typing function
                    searchbar.submit()
                    searchCount += 1
                    logging.info(f"[BING] {searchCount} searches completed (including additional terms)")

                    # Wait for 15 seconds before scrolling and opening the first result
                    sleep(15)

                    # Scroll through the search results page to mimic human behavior
                    for _ in range(15):
                        self.webdriver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
                        sleep(1)

                    # Open the first search result
                   first_result = WebDriverWait(self.webdriver, 10).until(
                        expected_conditions.element_to_be_clickable((By.CSS_SELECTOR, "h2 a"))
                    )
                    first_result.click()

                    # Stay on the first search result page for 120 seconds
                    sleep(120)

                    # Ensure delay between each related term search
                    sleep(randint(220, 280))
                except TimeoutException:
                    logging.warning(f"Timeout while searching for related term: {related_term}")

        return searchCount
