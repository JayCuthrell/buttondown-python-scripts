import requests
import json
from dotenv import load_dotenv
import os
from dateutil.parser import parse
from datetime import datetime, timedelta

# Get today's date
today = datetime.today()

# Calculate the date 7 days ago
seven_days_ago = today - timedelta(days=7)

# Format the date in YYYY-MM-DD format
formatted_date = seven_days_ago.strftime('%Y-%m-%d')

# The variable to store the date
date_seven_days_ago = formatted_date

print(date_seven_days_ago)

# Get a list of the recent emails from Buttondown

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


# Sort by publish_date in descending order (newest first)
    sorted_emails = sorted(all_emails, key=lambda email: parse(email["publish_date"]), reverse=False)

    # Get the last 7 emails  
    last_emails = sorted_emails

    # Enhanced console output
    print("Most Recent Buttondown Emails:")
    print("=" * 31)

    for email in last_emails:
        print(f"Subject: {email['subject']}")
        print(f"ID: {email['id']}")
        print(f"Publish Date: {email['publish_date']}")
        print(f"Status: {email['status']}")
        print(f"Type: {email['email_type']}")
        print("-" * 31)
else:
    print(f"Error: API request failed with status code {response.status_code}")

