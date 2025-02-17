import logging
import logging.config
import logging.handlers as handlers
import sys
import traceback
from datetime import datetime

from src import Browser, Searches
from src.utils import CONFIG, sendNotification, getProjectRoot

def setupLogging():
    _format = CONFIG.logging.format
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
        level=logging.getLevelName(CONFIG.logging.level.upper()),
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

def perform_searches(account, mobile):
    with Browser(mobile=mobile) as browser:
        searches = Searches(browser=browser)
        searches.performSearch(CONFIG['url'], CONFIG['duration'])

def main():
    setupLogging()

    search_type = CONFIG['search']['type']
    
    for account in CONFIG.accounts:
        try:
            logging.info(f"Starting searches for {account.email}")

            if search_type in ("desktop", "both"):
                logging.info("Performing desktop searches...")
                perform_searches(account, mobile=False)  # Perform desktop searches

            if search_type in ("mobile", "both"):
                logging.info("Performing mobile searches...")
                perform_searches(account, mobile=True)  # Perform mobile searches

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
