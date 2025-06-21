import requests
import json
from dotenv import load_dotenv
import os
import google.generativeai as genai
from datetime import datetime, timezone, timedelta

from dateutil.parser import parse
from datetime import datetime, timedelta, timezone

# Get today's date
today = datetime.today()

# Calculate the date 7 days ago
seven_days_ago = today - timedelta(days=-1)

# Format the date in YYYY-MM-DD format
formatted_date = seven_days_ago.strftime('%Y-%m-%d')

# The variable to store the date
date_seven_days_ago = formatted_date

# Load environment variables from .env file
load_dotenv()

# --- Buttondown API Configuration ---
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
if not BUTTONDOWN_API_KEY:
    raise ValueError("BUTTONDOWN_API_KEY not found in .env file")

BUTTONDOWN_BASE_URL = "https://api.buttondown.email"
BUTTONDOWN_ENDPOINT = "/emails"

# --- Google Gemini API Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

def get_latest_buttondown_email():
    """
    Fetches the latest published premium email from Buttondown.
    """
    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
    }
    # Fetching the latest email by ordering by publish_date descending and taking the first one
    # Note: Buttondown API might not directly support 'latest' or 'limit=1' easily without
    # sorting. We'll fetch a small number and sort locally if needed, or rely on default sorting.
    # For now, we'll assume the default API call without specific filters might return
    # recent ones and we'll pick the absolute latest from the results.
    # A more robust approach might involve `?ordering=-publish_date&limit=1` if the API supports it.
    FILTERS = f"&type=public&status=scheduled" # Attempt to get just one, the most recent

    try:
        response = requests.request("GET", f"{BUTTONDOWN_BASE_URL}/v1{BUTTONDOWN_ENDPOINT}?{FILTERS}", headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = json.loads(response.content)
        emails = data.get("results", [])

        if not emails:
            print("No emails found from Buttondown API.")
            return None

        # Sort by publish_date to ensure we get the absolute latest if page_size doesn't guarantee it
        emails.sort(key=lambda x: datetime.fromisoformat(x['publish_date'].replace('Z', '+00:00')), reverse=True)
        latest_email = emails[0]
        return latest_email

    except requests.exceptions.RequestException as e:
        print(f"Error fetching email from Buttondown: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response from Buttondown.")
        return None

def summarize_with_gemini(email_subject, email_body, email_url):
    """
    Uses Google Gemini to summarize the email content for LinkedIn,
    retaining writing style and adhering to LinkedIn repackaging strategy.
    """
    prompt = f"""
    You are an expert content repackager for LinkedIn. Your task is to summarize the following email content for a LinkedIn post.
    The summary needs to be engaging, value-driven, and adhere to the "Repackage and React Strategy" for LinkedIn.

    Here are the key guidelines for the LinkedIn post:
    - Always print the Email Subject exactly as the first line including the spicy emoji.
    - Include 2-4 insights or takeaways from the content that fits on the first few lines of a LinkedIn post to grab attention.
    - Include a takeaway for each day of the week from the headings related content and be sure to include the emoji per day without changing to be consistent and match the original content.
    - Make the value clear in the first two opening lines.
    - Open with your most interesting, eye-catching, or differentiated points.
    - Retain the original writing style of the email as much as possible.
    - Remember that the content is in reference to at least five (5) company names at a minimum.
    - Determine each and every company mentioned in each and every techmeme.com URL by extracting each and every one of the company names from the headlines of the articles referenced.
    - Include an exhaustive alphabetically ordered list of each and every one of company names referenced in the techmeme.com linked articles.
    - Include the link to the post {email_url} 
    - Do not use markdown style formatting such as asterisks or stars *

    ---
    Email Subject: {email_subject}
    ---
    Email Body:
    {email_body}

    Email URL: {email_url}
    ---

    Please provide a copy-paste ready LinkedIn post based on the above guidelines.
    """
    try:
        response = model.generate_content(prompt)
        # Access the text from the GenerateContentResponse object
        return response.text
    except Exception as e:
        print(f"Error generating summary with Gemini: {e}")
        return "Could not generate summary."

def main():
    latest_email = get_latest_buttondown_email()

    if latest_email:
        subject = latest_email.get('subject', 'No Subject')
        body = latest_email.get('body', 'No Body Content')
        email_url = latest_email.get('absolute_url', '#') # Get the direct URL of the email post

        print("-" * 50)
        print("Generating LinkedIn Post for the Latest Email...")
        print("-" * 50)

        linkedin_summary = summarize_with_gemini(subject, body, email_url)

        print("\n" * 2)
        print("Copy-Paste Ready LinkedIn Post:")
        print("=" * 30)
        print(linkedin_summary)
        print("\n")
        print(f"Read the full email here: {email_url}")
        print("=" * 30)
    else:
        print("Could not retrieve the latest email to generate a LinkedIn post.")

if __name__ == "__main__":
    main()
