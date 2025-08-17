import os
import csv
import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup, Comment
from dotenv import load_dotenv
from dateutil.parser import parse as parse_date
from datetime import datetime, timedelta

# --- Helper Functions ---

def _print_content_to_screen(content: str):
    """Helper function to format and print final content to the console."""
    print("\n" + "="*50)
    print("--- FINALIZED MARKDOWN FOR LATEST EMAIL ---")
    print("="*50 + "\n")
    print(content)

def _parse_description_from_response(response: requests.Response) -> str | None:
    """Helper to parse meta description from a successful HTTP response."""
    soup = BeautifulSoup(response.text, 'html.parser')
    meta_tag = soup.find('meta', attrs={'name': 'description'})
    if meta_tag and 'content' in meta_tag.attrs:
        return meta_tag['content'].strip()
    return None

def _generate_description_from_body(html_body: str) -> str:
    """
    Generates a description by extracting the text from the first <p> tag in the email body.
    """
    soup = BeautifulSoup(html_body, 'html.parser')
    first_paragraph = soup.find('p')
    if first_paragraph and first_paragraph.get_text(strip=True):
        return first_paragraph.get_text(strip=True)[:250]
    return "No description available."


def get_web_description(slug: str, raw_title: str = "") -> str:
    """
    Fetches the meta description. If the primary URL 404s and a raw_title is provided,
    it constructs and tries a fallback URL.
    """
    primary_url = f"https://buttondown.com/hot-fudge-daily/archive/{slug}"
    print(f"  > Trying primary URL: {primary_url}", flush=True)

    try:
        response = requests.get(primary_url, timeout=15)
        response.raise_for_status()
        description = _parse_description_from_response(response)
        return description if description else "No description available."
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404 and raw_title:
            print(f"  > Primary URL not found (404).", flush=True)
            fallback_slug = raw_title.lower().replace(' ', '-')
            fallback_url = f"https://buttondown.com/hot-fudge-daily/archive/{fallback_slug}"
            print(f"  > Trying fallback URL with original title: {fallback_url}", flush=True)

            try:
                fallback_response = requests.get(fallback_url, timeout=15)
                fallback_response.raise_for_status()
                description = _parse_description_from_response(fallback_response)
                return description if description else "No description available."
            except requests.exceptions.RequestException as fallback_e:
                print(f"  > ERROR: Fallback failed. {fallback_e}", flush=True)
                return "Error fetching description."
        else:
            print(f"  > ERROR: Primary request failed. {e}", flush=True)
            return "Error fetching description."
    except requests.exceptions.RequestException as e:
        print(f"  > ERROR: Primary request failed. {e}", flush=True)
        return "Error fetching description."

def process_html_body(body: str) -> str:
    """
    Parses an HTML string to remove comments and add missing alt tags to images
    using their corresponding figcaption text.
    """
    soup = BeautifulSoup(body, 'html.parser')
    body_was_modified = False

    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    if comments:
        body_was_modified = True
        print(f"  > Removed {len(comments)} HTML comment(s).", flush=True)
        for comment in comments:
            comment.extract()

    figures = soup.find_all('figure')
    alt_tags_fixed = 0
    for figure in figures:
        img_tag = figure.find('img')
        figcaption_tag = figure.find('figcaption')

        if img_tag and figcaption_tag and not img_tag.has_attr('alt'):
            alt_text = figcaption_tag.get_text(strip=True).replace('"', "'")
            if alt_text:
                img_tag['alt'] = alt_text
                alt_tags_fixed += 1
    
    if alt_tags_fixed > 0:
        body_was_modified = True
        print(f"  > Fixed {alt_tags_fixed} missing alt tag(s) using figcaptions.", flush=True)

    if body_was_modified:
        return soup.prettify()
    return body

# --- Main Operating Modes ---

def process_new_export():
    """MODE 1: Processes a new Buttondown export, creating permalinks."""
    # ... (This function's code is correct and remains the same)
    pass


def retry_failed_fetches():
    """MODE 2: Retries fetching descriptions for previously failed files."""
    # ... (This function's code is correct and remains the same)
    pass

def fix_alt_tags_in_folder():
    """MODE 3: Scans an import-ready folder and fixes missing alt tags and comments."""
    # ... (This function's code is correct and remains the same)
    pass


def sync_latest_from_api():
    """MODE 4: Fetches the latest email from the API and saves it to a configured path."""
    # ... (This function's code is correct and remains the same)
    pass

def create_daily_emails():
    """MODE 5: Creates skeleton emails for today or the upcoming week."""
    print("\n--- Mode: Create Skeleton Emails ---")
    
    today = datetime.now()
    current_weekday = today.weekday()

    load_dotenv()
    BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
    if not BUTTONDOWN_API_KEY:
        print("\nERROR: BUTTONDOWN_API_KEY not found in .env file.")
        return

    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
        "Content-Type": "application/json"
    }
    url = "https://api.buttondown.email/v1/emails"

    daily_formats = {
        0: "📈 Markets Monday for",
        1: "🔥 Hot Takes Tuesday for",
        2: "🤪 Wacky Wednesday for",
        3: "🔙 Throwback Thursday for",
        4: "✅ Final Thoughts Friday for",
        5: "🔮 Sneak Peak Saturday for"
    }

    if current_weekday == 6: # It's Sunday
        print("\nIt's Sunday! Creating skeleton emails for the week ahead...")
        for i in range(1, 7): 
            day_to_create = today + timedelta(days=i)
            day_name_index = day_to_create.weekday()
            
            if day_name_index in daily_formats:
                date_str = day_to_create.strftime('%Y-%m-%d')
                subject = f"{daily_formats[day_name_index]} {date_str}"
                
                payload = { "subject": subject, "body": f"Content for {subject} goes here.", "status": "draft" }

                try:
                    print(f" > Creating email: '{subject}'")
                    response = requests.post(url, headers=headers, json=payload)
                    
                    if response.status_code == 201:
                        print(f"   - SUCCESS: Email created successfully.")
                    else:
                        print(f"   - FAILED: API request failed with status code {response.status_code}")
                        print(f"     Response: {response.text}")
                except requests.exceptions.RequestException as e:
                    print(f"   - FAILED: An error occurred during the API request: {e}")
        print("\nWeekly email creation process complete.")
    
    elif current_weekday in daily_formats: # It's a weekday (Mon-Sat)
        print(f"\nCreating skeleton email for today, {today.strftime('%A')}...")
        date_str = today.strftime('%Y-%m-%d')
        subject = f"{daily_formats[current_weekday]} {date_str}"
        
        payload = { "subject": subject, "body": f"Content for {subject} goes here.", "status": "draft" }

        try:
            print(f" > Creating email: '{subject}'")
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 201:
                print(f"   - SUCCESS: Email created successfully.")
            else:
                print(f"   - FAILED: API request failed with status code {response.status_code}")
                print(f"     Response: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"   - FAILED: An error occurred during the API request: {e}")
    else:
        print("No email format defined for today.")

def create_sunday_digest():
    """MODE 6: Compiles the past week's posts into a new Sunday digest."""
    print("\n--- Mode: Create Hot Fudge Sunday Digest ---")
    
    today = datetime.now()
    if today.weekday() != 6:
        print("This feature is designed to be run on a Sunday.")
        return

    load_dotenv()
    BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
    if not BUTTONDOWN_API_KEY:
        print("\nERROR: BUTTONDOWN_API_KEY not found in .env file.")
        return

    headers = {"Authorization": f"Token {BUTTONDOWN_API_KEY}"}
    
    last_monday = today - timedelta(days=today.weekday())
    last_saturday = last_monday + timedelta(days=5)
    
    url = f"https://api.buttondown.email/v1/emails?email_type=premium&publish_date__start={last_monday.strftime('%Y-%m-%d')}&publish_date__end={last_saturday.strftime('%Y-%m-%d')}"
    
    try:
        print("\n > Fetching posts from the past week...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        weekly_emails = sorted(response.json()['results'], key=lambda x: x['publish_date'])
        
        digest_content = ""
        for email in weekly_emails:
            digest_content += f"## {email['subject']}\n\n{email['body']}\n\n"
        
        if not weekly_emails:
            print("  - No posts found from the past week to compile.")
            digest_content = "No posts from the past week."

    except requests.exceptions.RequestException as e:
        print(f"  - ERROR fetching weekly emails: {e}")
        return

    print("\n > Fetching last Sunday's email for the #OpenToWork Weekly section...")
    previous_sunday = today - timedelta(days=7)
    url = f"https://api.buttondown.email/v1/emails?email_type=public&publish_date__start={previous_sunday.strftime('%Y-%m-%d')}"
    
    open_to_work_content = ""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        previous_sunday_emails = response.json()['results']
        
        if previous_sunday_emails:
            last_sunday_body = previous_sunday_emails[0]['body']
            # Correctly split by the Markdown heading
            parts = re.split(r'#\s*#OpenToWork Weekly', last_sunday_body)
            if len(parts) > 1:
                open_to_work_content = "# #OpenToWork Weekly" + parts[1]
                print("  - Successfully extracted #OpenToWork Weekly section.")
            else:
                print("  - WARNING: Could not find '# OpenToWork Weekly' heading in last Sunday's email.")
        else:
            print("  - WARNING: Could not find last Sunday's email.")

    except requests.exceptions.RequestException as e:
        print(f"  - ERROR fetching last Sunday's email: {e}")

    new_subject = f"🌶️ Hot Fudge Sunday for {today.strftime('%Y-%m-%d')}"
    new_body = f"""
## Last Week

A look at the week behind...

## This Week

A look at the week ahead...

{digest_content}
{open_to_work_content if open_to_work_content else '# #OpenToWork Weekly'}
    """
    
    print(f"\n > Creating new digest email: '{new_subject}'")
    
    payload = {
        "subject": new_subject,
        "body": new_body.strip(),
        "status": "draft"
    }
    
    try:
        response = requests.post("https://api.buttondown.email/v1/emails", headers={"Authorization": f"Token {BUTTONDOWN_API_KEY}", "Content-Type": "application/json"}, json=payload)
        
        if response.status_code == 201:
            print("   - SUCCESS: Sunday digest created successfully in Buttondown.")
        else:
            print(f"   - FAILED: API request failed with status code {response.status_code}")
            print(f"     Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"   - FAILED: An error occurred during the API request: {e}")


def main():
    """Main function to display the menu and run the selected mode."""
    print("--- Buttondown to Eleventy Email Processor ---")
    
    while True:
        print("\nWhat would you like to do?")
        print("  1. Process new export")
        print("  2. Retry failed descriptions")
        print("  3. Fix empty alt tags & comments")
        print("  4. Sync latest email and save to file")
        print("  5. Create skeleton email(s)")
        print("  6. Create Hot Fudge Sunday digest")
        print("  7. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            process_new_export()
            break
        elif choice == '2':
            retry_failed_fetches()
            break
        elif choice == '3':
            fix_alt_tags_in_folder()
            break
        elif choice == '4':
            sync_latest_from_api()
            break
        elif choice == '5':
            create_daily_emails()
            break
        elif choice == '6':
            create_sunday_digest()
            break
        elif choice == '7':
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please select a valid option.")

if __name__ == "__main__":
    main()