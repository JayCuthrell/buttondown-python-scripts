import requests
import json
from dotenv import load_dotenv
import os
from dateutil.parser import parse
from datetime import datetime, timedelta, timezone

# Get today's date
today = datetime.today()

# Calculate the date 7 days ago
seven_days_ago = today - timedelta(days=7)

# Format the date in YYYY-MM-DD format
formatted_date = seven_days_ago.strftime('%Y-%m-%d')

# The variable to store the date
date_seven_days_ago = formatted_date

# print(date_seven_days_ago)

# Get a digest of recent emails from Buttondown

# Load environment variables from .env file
load_dotenv()

# Get the API key from the environment
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")

# Check if API key is available
if not BUTTONDOWN_API_KEY:
    raise ValueError("BUTTONDOWN_API_KEY not found in .env file")

headers = {
    "Authorization": f"Token {BUTTONDOWN_API_KEY}",
}

BASE_URL = "https://api.buttondown.email"
ENDPOINT = "/emails"
METHOD = "GET"
FILTERS = f"publish_date__start={date_seven_days_ago}&page=1&email_type=premium"

response = requests.request(METHOD, f"{BASE_URL}/v1{ENDPOINT}?{FILTERS}", headers=headers)

if response.status_code == 200:
    data = json.loads(response.content)
    all_emails = data.get("results", [])

    # Get current time in UTC to make it timezone-aware
    now_utc = datetime.now(timezone.utc) 
    six_days_ago = now_utc - timedelta(days=6)

    # Filter for recent emails
    recent_emails = [
        email 
        for email in all_emails 
        if parse(email['publish_date']) >= six_days_ago
    ]

    # Enhanced console output
    print("-" * 3)
    print(" " * 3)
    print("# Hot Fudge Daily Digest")
    print(" " * 3)
    print("-" * 3)

    if recent_emails:
        for email in recent_emails:
            print(f"## {email['subject']}")
            print(" " * 1)
            print(f"{email['body']}")
            print(" " * 3)
    else:
        print("No emails found within the last 6 days.")

else:
    print(f"Error: API request failed with status code {response.status_code}")
