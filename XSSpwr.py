import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
import argparse
import os

chrome_driver = None

class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"

def print_in_color(text, color):
    print(color + text + Colors.RESET)

# Function to get the ChromeDriver instance
def get_chrome_driver(headless=True):
    global chrome_driver
    if chrome_driver is None:
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')  # Run in headless mode
        chrome_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return chrome_driver

# Function to send payloads and capture the response
def send_payload(url, retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(url)
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}. Retrying ({attempt + 1}/{retries})...")
            time.sleep(5)
    return None

# Function to check if the payload triggers a popup
def check_popup(url):
    driver = get_chrome_driver()
    try:
        driver.get(url)
        time.sleep(2)
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            return True, alert_text
        except NoAlertPresentException:
            return False, None
    except UnexpectedAlertPresentException:
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            return True, alert_text
        except NoAlertPresentException:
            return False, None
    finally:
        pass

# Function to check if the payload triggers XSS
def check_xss(url, payload):
    driver = get_chrome_driver()
    try:
        driver.get(url)
        time.sleep(2)
        xss_marker = "xss_marker"
        script = f"""
        var xss_marker = document.createElement('div');
        xss_marker.id = '{xss_marker}';
        document.body.appendChild(xss_marker);
        """
        driver.execute_script(script)
        
        marker = driver.find_element(By.ID, xss_marker)
        if marker:
            return True
        return False
    except Exception as e:
        print(f"Error during XSS check: {e}")
        return False
    finally:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some URLs and payloads.')
    parser.add_argument('--payloads', required=True, help='Path to the payload file')
    parser.add_argument('--urls', required=True, help='Path to the URLs file')
    parser.add_argument('--headless', action='store_true', help='Run Chrome in headless mode')
    parser.add_argument('--retries', type=int, default=3, help='Number of retries for requests')

    args = parser.parse_args()

    if not os.path.exists(args.payloads) or not os.path.exists(args.urls):
        print_in_color("Error: Specified file(s) not found.", Colors.RED)
        exit(1)

    with open(args.urls, 'r') as url_file:
        urls = [line.strip() for line in url_file]

    with open(args.payloads, 'r') as payload_file:
        payloads = [line.strip() for line in payload_file]

    for url in urls:
        for payload in payloads:
            url_with_payload = url + payload
            response = send_payload(url_with_payload, args.retries)
            popup_triggered, alert_text = check_popup(url_with_payload)
            xss_triggered = check_xss(url_with_payload, payload)

            if popup_triggered:
                print_in_color(f"URL: {url_with_payload}, Payload: {payload} triggered a popup with alert text: {alert_text}", Colors.RED)
            elif xss_triggered:
                print_in_color(f"URL: {url_with_payload}, Payload: {payload} triggered XSS.", Colors.RED)
            else:
                print_in_color(f"URL: {url_with_payload}, Payload: {payload} did not trigger a popup or XSS.", Colors.GREEN)
            
            time.sleep(2)
    
    if chrome_driver:
        chrome_driver.quit()
