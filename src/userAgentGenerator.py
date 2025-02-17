import random
from typing import Any
import requests
from requests import HTTPError, Response
from src.utils import makeRequestsSession

class GenerateUserAgent:
    """A class for generating user agents for Microsoft Rewards Farmer."""

    MOBILE_DEVICE = "K"

    USER_AGENT_TEMPLATES = {
        "edge_pc": (
            "Mozilla/5.0"
            " ({system}) AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/{app[chrome_reduced_version]} Safari/537.36"
            " Edg/{app[edge_version]}"
        ),
        "edge_mobile": (
            "Mozilla/5.0"
            " ({system}) AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/{app[chrome_reduced_version]} Mobile Safari/537.36"
            " EdgA/{app[edge_version]}"
        ),
    }

    OS_PLATFORMS = {"win": "Windows NT 10.0", "android": "Linux"}
    OS_CPUS = {"win": "Win64; x64", "android": "Android 13"}

    def userAgent(self, browserConfig: dict[str, Any] | None, mobile: bool = False) -> tuple[str, dict[str, Any], Any]:
        system = self.getSystemComponents(mobile)
        app = self.getAppComponents(mobile)
        uaTemplate = self.USER_AGENT_TEMPLATES.get("edge_mobile") if mobile else self.USER_AGENT_TEMPLATES.get("edge_pc")

        newBrowserConfig = None
        if browserConfig is not None:
            platformVersion = browserConfig.get("userAgentMetadata")["platformVersion"]
        else:
            platformVersion = f"{random.randint(9,13) if mobile else random.randint(1,15)}.0.0"
            newBrowserConfig = {}
            newBrowserConfig["userAgentMetadata"] = {
                "platformVersion": platformVersion,
            }

        uaMetadata = {
            "mobile": mobile,
            "platform": "Android" if mobile else "Windows",
            "fullVersionList": [
                {"brand": "Not/A)Brand", "version": "99.0.0.0"},
                {"brand": "Microsoft Edge", "version": app["edge_version"]},
                {"brand": "Chromium", "version": app["chrome_version"]},
            ],
            "brands": [
                {"brand": "Not/A)Brand", "version": "99"},
                {"brand": "Microsoft Edge", "version": app["edge_major_version"]},
                {"brand": "Chromium", "version": app["chrome_major_version"]},
            ],
            "platformVersion": platformVersion,
            "architecture": "" if mobile else "x86",
            "bitness": "" if mobile else "64",
            "model": "",
        }

        return uaTemplate.format(system=system, app=app), uaMetadata, newBrowserConfig

    def getSystemComponents(self, mobile: bool) -> str:
        osId = self.OS_CPUS.get("android") if mobile else self.OS_CPUS.get("win")
        uaPlatform = self.OS_PLATFORMS.get("android") if mobile else self.OS_PLATFORMS.get("win")
        if mobile:
            osId = f"{osId}; {self.MOBILE_DEVICE}"
        return f"{uaPlatform}; {osId}"

    def getAppComponents(self, mobile: bool) -> dict[str, str]:
        edgeWindowsVersion, edgeAndroidVersion = self.getEdgeVersions()
        edgeVersion = edgeAndroidVersion if mobile else edgeWindowsVersion
        edgeMajorVersion = edgeVersion.split(".")[0]

        chromeVersion = self.getChromeVersion()
        chromeMajorVersion = chromeVersion.split(".")[0]
        chromeReducedVersion = f"{chromeMajorVersion}.0.0.0"

        return {
            "edge_version": edgeVersion,
            "edge_major_version": edgeMajorVersion,
            "chrome_version": chromeVersion,
            "chrome_major_version": chromeMajorVersion,
            "chrome_reduced_version": chromeReducedVersion,
        }

    def getEdgeVersions(self) -> tuple[str, str]:
        response = self.getWebdriverPage("https://edgeupdates.microsoft.com/api/products")

        def getValueIgnoreCase(data: dict, key: str) -> Any:
            for k, v in data.items():
                if k.lower() == key.lower():
                    return v
            return None

        data = response.json()
        if stableProduct := next((product for product in data if getValueIgnoreCase(product, "product") == "Stable"), None):
            releases = getValueIgnoreCase(stableProduct, "releases")
            androidRelease = next((release for release in releases if getValueIgnoreCase(release, "platform") == "Android"), None)
            windowsRelease = next((release for release in releases if getValueIgnoreCase(release, "platform") == "Windows" and getValueIgnoreCase(release, "architecture") == "x64"), None)
            if androidRelease and windowsRelease:
                return getValueIgnoreCase(windowsRelease, "productVersion"), getValueIgnoreCase(androidRelease, "productVersion")
        raise HTTPError("Failed to get Edge versions.")

    def getChromeVersion(self) -> str:
        response = self.getWebdriverPage("https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json")
        data = response.json()
        return data["channels"]["Stable"]["version"]

    @staticmethod
    def getWebdriverPage(url: str) -> Response:
        response = makeRequestsSession().get(url)
        if response.status_code != requests.codes.ok:
            raise HTTPError(f"Failed to get webdriver page {url}. Status code: {response.status_code}")
        return response
