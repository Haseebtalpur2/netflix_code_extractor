
import re
import os
import threading
import time
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import pdb
app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this to restrict origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the HTML Form
@app.get("/", response_class=HTMLResponse)
async def get_form():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(file_path, "r") as file:
        return HTMLResponse(content=file.read(), status_code=200)

# OTP Extraction Route
@app.post("/extract-otp", response_class=HTMLResponse)
async def extract_otp(email: str = Form(...)):
    # Initialize WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    
    # Variables to store HTML response
    html_response = "<h2>Results:</h2>"
    
    try:
        driver.get("https://maildrop.cc/inbox/?mailbox=charmingqwerty")
        time.sleep(2)
        
        emails = driver.find_elements(By.CLASS_NAME, 'message')
        email_list = [email.text for email in emails]
        
        # Iterate through emails
        for index, email_element in enumerate(emails, start=1):
            if index <= 4:
                email_element.click()
                time.sleep(1)
                
                try:
                    # Check if view message button is clickable
                    view_button = WebDriverWait(driver, 7).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="gatsby-focus-wrapper"]/div/main/div/div[1]/div/div/div[2]/div[1]/div/div[2]/button[1]'))
                    )
                    view_button.click()
                    source_code = driver.page_source
                    
                    # Search for the email within the page source code
                    email_match = re.search(re.escape(email), source_code)
                    
                    if email_match:
                        temp_pattern = r"https://www\.netflix\.com/account/travel/verify\?nftoken=[\S=]+"
                        hh_pattern = r"https://www\.netflix\.com/account/update-primary-location\?nftoken=[\S=]+"
                        
                        # Check for temporary code link
                        temp_matches = re.search(temp_pattern, source_code)
                        hh_matches = re.search(hh_pattern, source_code)
                        
                        if temp_matches:
                            get_code_url_entities = temp_matches.group()
                            driver.get(get_code_url_entities)
                            
                            try:
                                code_element = WebDriverWait(driver, 7).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-uia="travel-verification-otp"]'))
                                )
                                otp_code = code_element.text
                                html_response += f"<p>Extracted OTP Code: {otp_code}</p>"
                                break
                            except TimeoutException:
                                html_response += "<p>The temporary code link has expired, resend it and try again.</p>"
                                break
                        
                        # Check for household update link
                        elif hh_matches:
                            get_hh_url_entities = hh_matches.group()
                            driver.get(get_hh_url_entities)
                            
                            try:
                                confirm_hh = WebDriverWait(driver, 7).until(
                                    EC.presence_of_element_located((By.CLASS_NAME, "e1ax5wel2"))
                                )
                                confirm_hh.click()
                                WebDriverWait(driver, 7).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-uia="upl-success"]'))
                                )
                                html_response += "<p>Your household has been successfully updated.</p>"
                                break
                            except TimeoutException:
                                html_response += "<p>The household update link has expired, resend it and try again.</p>"
                                break
                        else:
                            html_response += "<p>Email found, but neither a temporary code nor household update link.</p>"
                            break
                except:
                    html_response += "<p>Something went wrong, please try again with correct email or maybe your code has expired.</p>"
                    break
            else:
                html_response += "<p>Unable to find a matching email. Try sending a new email.</p>"
                break
    finally:
        driver.quit()

    return HTMLResponse(content=html_response)
