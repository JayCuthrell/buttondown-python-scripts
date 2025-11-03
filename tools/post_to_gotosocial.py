import requests
import json
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone
import re
from markdownify import markdownify as md

# --- Load Environment Variables ---
load_dotenv()

# --- API Configurations ---
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
GOTOSOCIAL_INSTANCE_URL = os.getenv("GOTOSOCIAL_INSTANCE_URL")
GOTOSOCIAL_ACCESS_TOKEN = os.getenv("GOTOSOCIAL_ACCESS_TOKEN")

# --- Verification ---
if not all([BUTTONDOWN_API_KEY, GOTOSOCIAL_INSTANCE_URL, GOTOSOCIAL_ACCESS_TOKEN]):
    raise ValueError("One or more required environment variables are missing in your .env file.")

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

def format_for_gotosocial(subject, html_body, url):
    """
    Converts email HTML to a GoToSocial-friendly plain text format.
    """
    text = md(html_body, heading_style="ATX")

    # General cleanup
    text = text.replace('\\*', '*')
    text = text.replace('\\_', '_')
    text = re.sub(r'```[\s\S]*?```', '', text) # Remove code blocks
    # --- FIXED REGEX --- Only removes hashes at the start of a line
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE) 
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    # Construct the post
    full_post = f"{subject}\n\n{text}\n\nRead the full post here: {url}"
    
    return full_post

def post_to_gotosocial(post_content):
    """Posts the given content to GoToSocial."""
    headers = {
        "Authorization": f"Bearer {GOTOSOCIAL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    # The endpoint for posting a status in Mastodon/GoToSocial API
    post_url = f"{GOTOSOCIAL_INSTANCE_URL}/api/v1/statuses"
    
    post_data = {
        "status": post_content,
        "visibility": "public"  # Or "unlisted", "private", "direct"
    }

    try:
        response = requests.post(post_url, headers=headers, json=post_data)
        response.raise_for_status()
        print("\n✅ Successfully posted to GoToSocial!")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error posting to GoToSocial: {e}\n   Response: {e.response.text}")

def main():
    try:
        email_to_post = get_weekly_emails_and_prompt()

        if not email_to_post:
            print("No email selected. Exiting script.")
            return

        subject = email_to_post.get('subject', 'No Subject')
        body = email_to_post.get('body', 'No Body Content')
        email_url = email_to_post.get('absolute_url', '#')

        gotosocial_post = format_for_gotosocial(subject, body, email_url)

        print("\n" + "="*50)
        print("                DRY RUN")
        print("This will be posted to GoToSocial:")
        print("="*50 + "\n")
        print(gotosocial_post)
        print("\n" + "="*50)

        publish_choice = input("Do you want to publish this to GoToSocial? (y/N): ")
        if publish_choice.lower() == 'y':
            print("\nPublishing to GoToSocial...")
            post_to_gotosocial(gotosocial_post)
        else:
            print("\nPublishing cancelled.")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")

if __name__ == "__main__":
    main()