import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse

# Load env variables for the module
load_dotenv()
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
BUTTONDOWN_EDIT = os.getenv("BUTTONDOWN_EDIT")


# This function takes a subject and body content as input, and then sends a POST request
# to the Buttondown API to create a new draft email. It uses the BUTTONDOWN_API_KEY for
# authentication and can prepend an editor mode comment (like '<!-- buttondown-editor-mode: markdown -->')
# to the email body if the BUTTONDOWN_EDIT environment variable is set.

def post_to_buttondown(subject, body_content):    
    """Posts content to Buttondown as a draft email."""
    print("\n--- 📮 Posting to Buttondown... ---")
    if not BUTTONDOWN_API_KEY:
        print("❌ BUTTONDOWN_API_KEY not found.")
        return

    headers = {"Authorization": f"Token {BUTTONDOWN_API_KEY}", "Content-Type": "application/json"}
    url = "https://api.buttondown.email/v1/emails"
    editor_mode_comment = f"{BUTTONDOWN_EDIT}" if BUTTONDOWN_EDIT else ""
    final_body = f"{editor_mode_comment}\n{body_content}"
    payload = {"subject": subject, "body": final_body, "status": "draft", "email_type": "premium"}

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            print(f"✅ Successfully created draft in Buttondown.")
        else:
            print(f"❌ Failed to create draft. Status: {response.status_code}\n   Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")


# This function fetches the most recent public Sunday email from Buttondown.
# It filters emails by publish date and ensures the email was published on a Sunday.

def get_latest_sunday_buttondown_email():
    """Fetches the most recent public Sunday email from Buttondown."""
    headers = {"Authorization": f"Token {BUTTONDOWN_API_KEY}"}
    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
    formatted_date = two_weeks_ago.strftime('%Y-%m-%d')
    FILTERS = f"?ordering=-publish_date&type=public&publish_date__start={formatted_date}"
    url = f"https://api.buttondown.email/v1/emails{FILTERS}"

    try:
        print(f"▶️ Fetching recent public emails from Buttondown (since {formatted_date})...")
        # ... (rest of the function logic from linkedin_post_generator.py)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = json.loads(response.content)
        emails = data.get("results", [])
        
        if not emails:
            print("No emails found...")
            return None

        for email in emails:
            publish_date_str = email.get('publish_date')
            if publish_date_str:
                publish_date = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
                if publish_date.weekday() == 6: # 6 = Sunday
                    print(f"✅ Found latest Sunday email.")
                    return email
        
        print("No Sunday email found.")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching email from Buttondown: {e}")
        return None

# Alternative implementation of fetching the latest Sunday email
# This version filters by a date range to ensure we capture the most recent Sunday.

def get_latest_sunday_buttondown_email_alt():
    """
    Fetches the most recent public email from Buttondown that was published on a Sunday.
    This version filters by a date range to ensure we capture the most recent Sunday.
    """
    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
    }
    
    # Calculate the date 14 days ago to ensure we capture at least two weeks of emails.
    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
    
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

# This function fetches all public emails from the last 7 days and prompts the user to select one.
# It then returns the selected email's data.

def get_weekly_emails_and_prompt():
    """
    Fetches all public emails from the last 7 days and prompts the user to select one.
    """
    headers = {"Authorization": f"Token {BUTTONDOWN_API_KEY}"}
    
    today = datetime.now(timezone.utc)
    start_date = today - timedelta(days=7)
    start_date_str = start_date.strftime('%Y-%m-%d')
    
    url = f"https://api.buttondown.email/v1/emails?ordering=-publish_date&type=public&publish_date__start={start_date_str}"

    try:
        print(f"▶️ Fetching emails since {start_date_str} from Buttondown...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        emails = response.json().get("results", [])

        if not emails:
            print("⏹️ No emails found in the last 7 days.")
            return None

        print("\n--- Emails Found in the Last 7 Days ---")
        for i, email in enumerate(emails):
            publish_date = datetime.fromisoformat(email['publish_date'].replace('Z', '+00:00'))
            date_display = publish_date.strftime('%Y-%m-%d (%a)')
            print(f"  {i + 1}. {date_display} - {email['subject']}")
        print("-" * 30)

        choice = input("Enter the number of the email to post (or press Enter to cancel): ")

        if not choice.strip():
            return None

        index = int(choice) - 1
        if 0 <= index < len(emails):
            selected_email = emails[index]
            print(f"✅ Selected: '{selected_email['subject']}'")
            return selected_email
        else:
            print("❌ Invalid number.")
            return None

    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"❌ An error occurred: {e}")
        return None