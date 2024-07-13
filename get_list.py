import requests
import json
from dotenv import load_dotenv
import os
from datetime import datetime

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

response = requests.request(METHOD, f"{BASE_URL}/v1{ENDPOINT}", headers=headers)

if response.status_code == 200:
    data = json.loads(response.content)
    all_emails = data.get("results", [])

    # Sort emails by publish_date in descending order (newest first)
    sorted_emails = sorted(
        all_emails,
        key=lambda email: datetime.fromisoformat(email["publish_date"]), 
        reverse=True
    )

    # Get the 6 most recent emails
    most_recent_emails = sorted_emails[:6]

    # Enhanced console output
    print("6 Most Recent Buttondown Emails:")
    print("=" * 31)

    for email in most_recent_emails:
        print(f"Subject: {email['subject']}")
        print(f"ID: {email['id']}")
        print(f"Publish Date: {email['publish_date']}")
        print(f"Status: {email['status']}")
        print("-" * 31)
else:
    print(f"Error: API request failed with status code {response.status_code}")

