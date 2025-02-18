import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def save_cookies(driver, path):
    with open(path, 'w') as file:
        json.dump(driver.get_cookies(), file)

def login_youtube():
    with open('youtube_credentials.json', 'r') as file:
        credentials = json.load(file)

    email = credentials['email']
    password = credentials['password']

    driver = webdriver.Chrome()
    driver.get("https://accounts.google.com/signin")

    wait = WebDriverWait(driver, 10)
    email_field = wait.until(EC.element_to_be_clickable((By.ID, "identifierId")))
    email_field.send_keys(email)
    next_button = wait.until(EC.element_to_be_clickable((By.ID, "identifierNext")))
    next_button.click()

    password_field = wait.until(EC.element_to_be_clickable((By.NAME, "password")))
    password_field.send_keys(password)
    login_button = wait.until(EC.element_to_be_clickable((By.ID, "passwordNext")))
    login_button.click()

    logging.info("Logged in to YouTube. Please solve the CAPTCHA and/or enter the 2FA code if prompted.")

    # Wait for CAPTCHA and 2FA completion
    start_time = time.time()
    timeout = 600  # Set a longer timeout (10 minutes) for manual intervention
    while time.time() - start_time < timeout:
        if "youtube.com" in driver.current_url:
            logging.info("CAPTCHA and/or 2FA completed, logged in to YouTube.")
            break
        logging.info("Waiting for CAPTCHA and/or 2FA completion...")
        time.sleep(5)  # Check every 5 seconds

    save_cookies(driver, 'youtube_cookies.json')
    driver.quit()

if __name__ == "__main__":
    login_youtube()
