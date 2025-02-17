import yaml
from pathlib import Path
from typing import Any, Self
import json
import requests
import logging
import apprise

class Config(dict):
    @classmethod
    def fromYaml(cls, path: Path) -> Self:
        if not path.exists() or not path.is_file():
            return cls()
        with open(path, encoding="utf-8") as f:
            yamlContents = yaml.safe_load(f)
            if not yamlContents:
                return cls()
            return cls(yamlContents)

    def __getattr__(self, item):
        return self[item]

def getProjectRoot() -> Path:
    return Path(__file__).parent.parent

def getBrowserConfig(sessionPath: Path) -> dict | None:
    configFile = sessionPath / "config.json"
    if not configFile.exists():
        return
    with open(configFile, "r") as f:
        return json.load(f)

def saveBrowserConfig(sessionPath: Path, config: dict) -> None:
    configFile = sessionPath / "config.json"
    with open(configFile, "w") as f:
        json.dump(config, f)

def makeRequestsSession() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session

def sendNotification(title: str, message: str, e: Exception = None) -> None:
    # Log the notification locally
    logging.info(f"{title}: {message}")
    if e:
        logging.error(e)

    # Send the notification using Apprise
    apobj = apprise.Apprise()
    discord_webhook_url = CONFIG.get("discord_webhook_url")
    if discord_webhook_url:
        apobj.add(discord_webhook_url)
        apobj.notify(
            body=message,
            title=title
        )

CONFIG = Config.fromYaml(getProjectRoot() / "config.yaml")
