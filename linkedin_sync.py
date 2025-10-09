import requests
import json
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone
import re
from markdownify import markdownify as md

# Load environment variables from .env file
load_dotenv()

# --- API Configurations ---
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_USER_ID = os.getenv("LINKEDIN_USER_ID")
LINKEDIN_AUTHOR = os.getenv("LINKEDIN_AUTHOR")  # e.g., "urn:li:person:xxxxxxxx"

# --- Verification ---
if not all([BUTTONDOWN_API_KEY, LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR]):
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


def format_for_linkedin(subject, description, html_body, url):
    """
    Converts email HTML to a LinkedIn-friendly plain text format with footnote-style links.
    """

    footnotes = []
    def link_to_footnote(match):
        link_text = match.group(1)
        link_url = match.group(2)
        footnotes.append(link_url)
        return f"{link_text} [{len(footnotes)}]"

    def convert_md_table_to_list(match):
        table_text = match.group(0)
        lines = table_text.strip().split('\n')
        if len(lines) < 3: return table_text

        list_items = []
        for row in lines[2:]:
            columns = [col.strip() for col in row.split('|') if col.strip()]
            if len(columns) >= 3:
                symbol_match = re.search(r'\[(.*?)\]', columns[0])
                symbol = symbol_match.group(1) if symbol_match else columns[0]
                company = columns[1]
                change = columns[2]
                list_items.append(f"• {symbol} ({company}): {change}")
        return "\n".join(list_items)

    text = md(html_body, heading_style="ATX")

    # --- THE FIX IS HERE ---
    # Un-escape special characters that markdownify might have escaped in URLs and text
    text = text.replace('\\*', '*')
    text = text.replace('\\$', '$')
    text = text.replace('\\_', '_') # Fix for underscores in URLs
    
    text = re.sub(r'\{\{.*?\}\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(https?://[^\s]+)\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*---\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    table_pattern = re.compile(r'^\s*\|.*\|.*\n\s*\|[-|: ]+\|.*\n((?:\s*\|.*\|.*\n?)+)', re.MULTILINE)
    text = table_pattern.sub(convert_md_table_to_list, text)
    
    text = re.sub(r'\*\s*\[.*?\]\(.*?\)\s*\((.*?)\):\s*\*\*(.*?)\*\*', r'• \1: \2', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', link_to_footnote, text)

    # Add spacing for sub-headers (####)
    text = re.sub(r'#+\s*(Wacky Wonderful|Wayback|Whoa)', r'\n\1\n', text, flags=re.IGNORECASE)
    
    text = re.sub(r'#+\s*(Last Week|This Week)', r'\n\n\1\n', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*📈\s*Markets Monday.*', '\n\n📈 Markets Monday\n', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🔥\s*Hot Takes Tuesday.*', '\n\n🔥 Hot Takes Tuesday\n', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🤪\s*Wacky Wednesday.*', '\n\n🤪 Wacky Wednesday\n', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🔙\s*Throwback Thursday.*', '\n\n🔙 Throwback Thursday\n', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*✅\s*Final Thoughts Friday.*', '\n\n✅ Final Thoughts Friday\n', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🔮\s*Sneak Peak Saturday.*', '\n\n🔮 Sneak Peak Saturday\n', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*#OpenToWork Weekly.*', '\n\n👀 #OpenToWork Weekly\n', text, flags=re.IGNORECASE)
    
    text = re.sub(r'(\*\*|__)', '', text) # Remove bold markers
    
    # Handle both '*' and '-' for lists, and remove leading whitespace
    text = re.sub(r'^\s*[\*\-]\s*', '• ', text, flags=re.MULTILINE)
    
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    footnote_section = ""
    if footnotes:
        footnote_lines = [f"[{i+1}] {url}" for i, url in enumerate(footnotes)]
        footnote_section = "\n\n" + "\n".join(footnote_lines)

    full_post = f"{subject}\n\n{description}\n\n{text}{footnote_section}\n\nRead the full post here: {url}"
    return full_post


def post_to_linkedin(post_content):
    """Posts the given content to LinkedIn, including the required version header."""
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "x-li-format": "json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    post_data = {
        "author": f"{LINKEDIN_AUTHOR}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_content},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    try:
        response = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=post_data)
        response.raise_for_status()
        print("\n✅ Successfully posted to LinkedIn!")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error posting to LinkedIn: {e}\n   Response: {e.response.text}")

def main():
    try:
        email_to_post = get_weekly_emails_and_prompt()

        if not email_to_post:
            print("No email selected. Exiting script.")
            return

        subject = email_to_post.get('subject', 'No Subject')
        description = email_to_post.get('description', '')
        body = email_to_post.get('body', 'No Body Content')
        email_url = email_to_post.get('absolute_url', '#')

        linkedin_post = format_for_linkedin(subject, description, body, email_url)

        print("\n" + "="*50)
        print("                DRY RUN")
        print("This will be posted to LinkedIn:")
        print("="*50 + "\n")
        print(linkedin_post)
        print("\n" + "="*50)

        publish_choice = input("Do you want to publish this to LinkedIn? (y/N): ")
        if publish_choice.lower() == 'y':
            print("\nPublishing to LinkedIn...")
            post_to_linkedin(linkedin_post)
        else:
            print("\nPublishing cancelled.")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")

if __name__ == "__main__":
    main()