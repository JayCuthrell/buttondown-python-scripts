import requests
import json
from dotenv import load_dotenv
import os
import google.generativeai as genai
from datetime import datetime, timedelta, timezone

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
model = genai.GenerativeModel('gemini-2.5-pro')

def get_latest_sunday_buttondown_email():
    """
    Fetches the most recent public email from Buttondown that was published on a Sunday.
    This version filters by a date range to ensure we capture the most recent Sunday.
    """
    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
    }
    
    # Calculate the date 14 days ago to ensure we capture at least two weeks of emails.
    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Format the date into a simple YYYY-MM-DD format.
    formatted_date = two_weeks_ago.strftime('%Y-%m-%d')
    
    # Use the publish_date__start filter to get all emails published in the last 14 days.
    FILTERS = f"?ordering=-publish_date&type=public&publish_date__start={formatted_date}"

    try:
        print("Fetching recent public emails from Buttondown (last 14 days)...")
        response = requests.get(f"{BUTTONDOWN_BASE_URL}/v1{BUTTONDOWN_ENDPOINT}{FILTERS}", headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = json.loads(response.content)
        emails = data.get("results", [])

        if not emails:
            print("No emails found from Buttondown API in the specified date range.")
            return None

        # Iterate through the fetched emails to find the most recent one published on a Sunday.
        for email in emails:
            publish_date_str = email.get('publish_date')
            if publish_date_str:
                # The 'Z' at the end of the timestamp indicates UTC. `fromisoformat` can handle this.
                publish_date = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
                
                # Check if the day of the week is Sunday.
                # Monday is 0 and Sunday is 6.
                if publish_date.weekday() == 6:
                    print(f"Found latest Sunday email published on {publish_date.date()}.")
                    return email

        print("No Sunday email found in the recent batch of emails.")
        return None

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
    latest_email = get_latest_sunday_buttondown_email()

    if latest_email:
        subject = latest_email.get('subject', 'No Subject')
        body = latest_email.get('body', 'No Body Content')
        email_url = latest_email.get('absolute_url', '#') 

        print("-" * 50)
        print("Generating LinkedIn Post for the Latest Sunday Email...")
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
        print("Could not retrieve the latest Sunday email to generate a LinkedIn post.")

if __name__ == "__main__":
    main()
