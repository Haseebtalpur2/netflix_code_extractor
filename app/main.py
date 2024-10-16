

import re
import os
import threading
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from selenium.common.exceptions import TimeoutException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Form
import pdb

app = FastAPI()

# Global lock variables
lock_active = False
lock_expiration_time = None
get_code_url = None

# Function to release the lock after 3 minutes
def release_lock():
    global lock_active, lock_expiration_time
    threading.Timer(180, lambda: set_lock(False)).start()

# Function to set or unset the lock
def set_lock(status: bool):
    global lock_active, lock_expiration_time
    lock_active = status
    lock_expiration_time = datetime.now() + timedelta(minutes=0.5) if status else None

# Route to serve the form HTML (optional)
@app.get("/", response_class=HTMLResponse)
async def get_form():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(file_path, "r") as file:
        return HTMLResponse(content=file.read(), status_code=200)

# Route to extract OTP from the fixed inbox
@app.post("/extract-otp")
async def extract_otp(email: str = Form(...)):
    global get_code_url

    # global lock_active

    # if lock_active:
    #     raise HTTPException(status_code=429, detail="Request is locked. Please try again later.")

    # # Set the lock
    # set_lock(True)

    try:
        # Setup Selenium with headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)
        # Access the fixed Maildrop inbox
        inbox_url = "https://maildrop.cc/inbox/?mailbox=charmingqwerty"
        driver.get(inbox_url)
        # Find and click the "View Message" button
        view_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="gatsby-focus-wrapper"]/div/main/div/div[1]/div/div/div[2]/div[1]/div/div[2]/button[1]'))
        )
        view_button.click()

        # Get the page source and search for the email directly
        source_code = driver.page_source
        # email_to_check = email
        # pattern = r'This message was mailed to\\s*<a[^>]+>\\[([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})\\]</a>\\s*by Netflix'
        # matching_email = re.escape(email_to_check) 
        pattern = r"https://www\.netflix\.com/account/travel/verify\?nftoken=[\S=]+"
        match = re.search(pattern, source_code)
        if not match:
            raise HTTPException(status_code=404, detail="Code link not found")

        get_code_url = match.group(0)

        # Navigate to the "Get Code" link to retrieve the OTP
        # temporary link
        # get_code_url = "file:///Users/dev/Downloads/Netflix1.htm"
        driver.get(get_code_url)
        otp_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "challenge-code"))
        )

        try:
            # Attempt to find the OTP element
            otp_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "challenge-code"))
            )
            otp_code = otp_element.text
            return {"otp": otp_code}

        except TimeoutException:
            # If OTP element is not found, check for the Confirm update button using full XPath
            try:
                confirm_button = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div/div[2]/div/div/div/div[4]/button"))
                )
                # Return a message or HTML indicating the button is found
                return {"message": "Confirm update button found", "button_html": confirm_button.get_attribute('outerHTML'), "get_code_url": get_code_url }
            except TimeoutException:
                return {"error": "Neither the challenge code nor the Confirm update button was found."}

    except Exception as e:
        return {"error": str(e)}

    finally:
        # Release the lock after completion
        release_lock()
        driver.quit()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.post("/confirm-otp")
async def confirm_otp():
    global get_code_url
    # Set up Selenium WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    # get_code_url = "file:///Users/dev/Downloads/Netflix1.htm"
    driver.get(get_code_url)
    # Wait for the confirm button and click it
    try:
        confirm_button = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div/div[2]/div/div/div/div[4]/button"))
        )
        confirm_button.click()
        return {"message": "House Hold OTP confirmed successfully."}
    except Exception as e:
        return {"detail": str(e)}
    finally:
        get_code_url = None
        driver.quit()