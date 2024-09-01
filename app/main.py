from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
import imaplib
import email as email_module  # Renaming the imported email module to avoid conflict
from email.header import decode_header
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

from datetime import datetime, timedelta
import threading

app = FastAPI()

# Global lock and expiration time variables
lock_active = False
lock_expiration_time = None

# Serve the HTML page
@app.get("/", response_class=HTMLResponse)
async def get_form():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(file_path, "r") as file:
        return HTMLResponse(content=file.read(), status_code=200)

# Function to release the lock
def release_lock():
    global lock_active
    global lock_expiration_time

    # Sleep for 3 minutes
    threading.Timer(180, lambda: set_lock(False)).start()

# Function to set or unset the lock
def set_lock(status: bool):
    global lock_active
    global lock_expiration_time

    lock_active = status
    if status:
        lock_expiration_time = datetime.now() + timedelta(minutes=3)
    else:
        lock_expiration_time = None

# Extract OTP based on the provided email
@app.post("/extract-otp")
async def extract_otp(email: str = Form(...)):
    global lock_active
    global lock_expiration_time

    # Check if lock is active
    if lock_active:
        remaining_time = (lock_expiration_time - datetime.now()).seconds
        if remaining_time > 0:
            raise HTTPException(status_code=429, detail=f"Please wait {remaining_time // 60} minutes and {remaining_time % 60} seconds before trying again.")
        else:
            set_lock(False)  # Release the lock if the time has passed

    # Set the lock
    set_lock(True)

    # Call the release_lock function to release the lock after 3 minutes
    release_lock()

    # imap setup
    server = "outlook.office365.com"
    port = 993
    username = "charmingtalpur@outlook.com"
    password = "Thehash@@2"

    # Connect to the IMAP server & login
    mail = imaplib.IMAP4_SSL(server, port)
    mail.login(username, password)
    mail.select("inbox")
    search_criteria = f'(TO "{email}")'
    status, messages = mail.search(None, search_criteria)

    if status == "OK":
        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} emails matching the criteria.")
    else:
        return {"error": "No emails found"}

    # Fetch the latest email
    latest_email_id = email_ids[-1]
    status, msg_data = mail.fetch(latest_email_id, "(RFC822)")

    # Parse the email content
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email_module.message_from_bytes(response_part[1])
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else 'utf-8')
            print(f"Subject: {subject}")

            from_ = msg.get("From")
            print(f"From: {from_}")

            # Initialize a variable to store the email body
            email_body = ""

            # If the email message is multipart
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    try:
                        # Extract the body content
                        part_body = part.get_payload(decode=True).decode()
                        email_body += part_body
                    except Exception as e:
                        pass
            else:
                # If it's a single-part email, directly get the body
                content_type = msg.get_content_type()
                email_body = msg.get_payload(decode=True).decode()

            # Extract URLs from the email body using regex
            pattern = r'https://www\.netflix\.com/account/travel/verify\S*'
            urls = re.findall(pattern, email_body)

            # Check if there is a second URL and save it as important_url
            important_url = urls[1] if len(urls) > 1 else None
            #important_url = 'http://127.0.0.1:8000/file:///Users/dev/Documents/dev_projects/interview%20material/Devsinc%20Resumes/Netflix.html'
            print(important_url)
            if important_url:
                # Set up Selenium in headless mode
                chrome_options = Options()
                chrome_options.add_argument("--headless")  # Run in headless mode
                chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration (not necessary but good practice)
                chrome_options.add_argument("--no-sandbox")  # Needed for running as root in some environments
                chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

                # Initialize the WebDriver
                driver = webdriver.Chrome(options=chrome_options)

                try:
                    # Navigate to the URL
                    driver.get(important_url)

                    # Wait until the page loads and the element with the class "challenge-code" is found
                    wait = WebDriverWait(driver, 5)  # Adjust the timeout as necessary
                    otp_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "challenge-code")))

                    # Extract the OTP from the element
                    otp = otp_element.text
                    print(f"The OTP is: {otp}")
                    return {"otp": otp}

                except Exception as e:
                    print(f"An error occurred: {e}")
                    return {"error": str(e)}

                finally:
                    driver.quit()  # Make sure to close the browser after the task is done

            else:
                return {"error": "Important URL not found in the email body."}

    return {"error": "No valid OTP found"}
