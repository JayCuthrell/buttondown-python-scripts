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
        return str(soup)
    return body

# --- Main Operating Modes ---

def process_new_export():
    """MODE 1: Processes a new Buttondown export, creating permalinks."""
    print("\n--- Mode: Process New Buttondown Export ---")
    export_dir_str = input("Enter the path to the Buttondown export directory: ")
    export_dir = Path(export_dir_str).expanduser()
    csv_path = export_dir / "emails.csv"
    emails_folder_path = export_dir / "emails"

    if not all([export_dir.is_dir(), csv_path.is_file(), emails_folder_path.is_dir()]):
        print(f"\nERROR: The provided directory '{export_dir}' is not valid.")
        return

    output_dir = export_dir.parent / "emails_ready_for_import"
    output_dir.mkdir(exist_ok=True)
    
    skip_choice = input("Do you want to skip files that already exist in the output folder? (y/n): ").lower()
    skip_existing = skip_choice == 'y'

    print(f"\nProcessing files... Output will be in: {output_dir}")

    try:
        processed_count = 0
        skipped_count = 0
        with open(csv_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                slug = row.get('slug')
                if not slug:
                    continue
                
                output_file = output_dir / f"{slug}.md"
                
                if skip_existing and output_file.exists():
                    skipped_count += 1
                    continue
                
                print(f"\nProcessing new email: {slug}")
                processed_count += 1
                
                raw_subject = row.get('subject', 'No Subject')
                final_title = raw_subject.replace('"', "'")
                permalink = f"/archive/{slug}/"
                description = get_web_description(slug, raw_subject).replace('"', "'")
                
                source_md_path = emails_folder_path / f"{slug}.md"
                if not source_md_path.is_file():
                    print(f"  > ERROR: Markdown file not found at {source_md_path}. Skipping.")
                    continue
                
                original_body = source_md_path.read_text(encoding='utf-8')
                processed_body = process_html_body(original_body)
                
                frontmatter = f"""---
title: "{final_title}"
permalink: "{permalink}"
description: "{description}"
date: {row.get('publish_date')}
---

"""
                final_content = frontmatter + processed_body
                output_file.write_text(final_content, encoding='utf-8')
                print(f"  > Successfully created: {slug}.md")
        
        print("\n--- Export Processing Complete! ---")
        print(f"Processed {processed_count} new file(s).")
        if skip_existing:
            print(f"Skipped {skipped_count} existing file(s).")

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


def retry_failed_fetches():
    """MODE 2: Retries fetching descriptions for previously failed files."""
    print("\n--- Mode: Retry Failed Descriptions ---")
    import_dir_str = input("Enter the path to the 'emails_ready_for_import' directory: ")
    import_dir = Path(import_dir_str).expanduser()
    if not import_dir.is_dir():
        print(f"\nERROR: The directory '{import_dir}' does not exist.")
        return

    print(f"\nScanning for files with errors in: {import_dir}")
    error_string_to_find = 'description: "Error fetching description."'
    files_to_retry = [
        md_file for md_file in import_dir.glob("*.md")
        if error_string_to_find in md_file.read_text(encoding='utf-8')
    ]
    
    if not files_to_retry:
        print("No files with fetching errors were found.")
        return

    print(f"Found {len(files_to_retry)} file(s) to retry.")
    for md_file in files_to_retry:
        slug = md_file.stem
        content = md_file.read_text(encoding='utf-8')
        title_match = re.search(r'^title:\s*"(.*?)"', content, re.MULTILINE)
        title = title_match.group(1) if title_match else ""

        print(f"\nRetrying email with slug: {slug}")
        
        new_description = get_web_description(slug, title).replace('"', "'")

        if new_description != "Error fetching description." and new_description != "No description available.":
            new_desc_line = f'description: "{new_description}"'
            updated_content = re.sub(r'^description:.*$', new_desc_line, content, count=1, flags=re.MULTILINE)
            md_file.write_text(updated_content, encoding='utf-8')
            print(f"  > SUCCESS: Updated {md_file.name}")
        else:
            print(f"  > FAILED: Could not retrieve a new description for {slug}.")

def fix_alt_tags_in_folder():
    """MODE 3: Scans an import-ready folder and fixes missing alt tags and comments."""
    print("\n--- Mode: Fix Empty Alt Tags & Comments ---")
    import_dir_str = input("Enter the path to the 'emails_ready_for_import' directory: ")
    import_dir = Path(import_dir_str).expanduser()
    if not import_dir.is_dir():
        print(f"\nERROR: The directory '{import_dir}' does not exist.")
        return

    print(f"\nScanning files in: {import_dir}")
    updated_files_count = 0
    
    for md_file in import_dir.glob("*.md"):
        original_content = md_file.read_text(encoding='utf-8')
        modified_content = process_html_body(original_content)
        
        if modified_content != original_content:
            print(f"Updating: {md_file.name}")
            md_file.write_text(modified_content, encoding='utf-8')
            updated_files_count += 1

    print("\n--- Fixes Complete! ---")
    if updated_files_count > 0:
        print(f"Successfully updated {updated_files_count} file(s).")
    else:
        print("No files needed fixing.")


def sync_latest_from_api():
    """MODE 4: Fetches emails from the API for the current week and allows syncing of missing ones."""
    print("\n--- Mode: Sync Email from API ---")
    
    load_dotenv()
    BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
    SYNC_PATH_STR = os.getenv("SYNC_PATH")

    if not all([BUTTONDOWN_API_KEY, SYNC_PATH_STR]):
        print("\nERROR: BUTTONDOWN_API_KEY or SYNC_PATH not found in .env file.")
        return

    SYNC_PATH = Path(SYNC_PATH_STR).expanduser()
    if not SYNC_PATH.is_dir():
        print(f"\nERROR: SYNC_PATH '{SYNC_PATH_STR}' is not a valid directory.")
        return

    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    
    headers = {"Authorization": f"Token {BUTTONDOWN_API_KEY}"}
    url = f"https://api.buttondown.email/v1/emails?email_type=premium&publish_date__start={start_of_week.strftime('%Y-%m-%d')}"
    
    try:
        print(f" > Checking for missing emails for the week of {start_of_week.strftime('%Y-%m-%d')}...", flush=True)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        api_emails = response.json().get("results", [])
        
        missing_emails_map = {}
        
        print("\nWhich day would you like to sync?")
        
        for i in range(today.weekday() + 1):
            day_to_check = start_of_week + timedelta(days=i)
            day_name = day_to_check.strftime('%A')
            date_str = day_to_check.strftime('%Y-%m-%d')
            
            email_for_day = next((e for e in api_emails if day_name in e.get('subject', '') and date_str in e.get('subject', '')), None)

            if email_for_day:
                slug = email_for_day.get('slug')
                day_directory = SYNC_PATH / day_name
                expected_file = day_directory / f"{slug}.md"
                status = "[Synced]" if expected_file.exists() else "[Missing]"
                
                if status == "[Missing]":
                    missing_emails_map[i + 1] = email_for_day

                print(f"  {i + 1}. {day_name} ({date_str}) - {status} - \"{email_for_day['subject']}\"")
            else:
                print(f"  {i + 1}. {day_name} ({date_str}) - [No Email Published]")

        if not missing_emails_map:
            print("\nNo missing emails found to sync.")
            return

        choice = input("\nEnter the number of the day to sync (or press Enter to cancel): ").strip()

        if not choice.isdigit() or int(choice) not in missing_emails_map:
            print("Invalid selection or nothing to sync. Exiting.")
            return
            
        email_to_sync = missing_emails_map[int(choice)]

        print(f"\n > Processing email: '{email_to_sync['subject']}'")

        raw_subject = email_to_sync.get('subject', 'No Subject')
        slug = email_to_sync.get('slug', '')
        original_body = email_to_sync.get('body', '')
        
        description = email_to_sync.get('description')
        if not description:
            print("  > API 'description' not found. Generating from email body...", flush=True)
            description = _generate_description_from_body(original_body)
        else:
            print("  > Using 'description' field from API.", flush=True)

        description = description.replace('"', "'")
        final_title = raw_subject.replace('"', "'")
        permalink = f"/archive/{slug}/"
        
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', raw_subject)
        if date_match:
            formatted_date = date_match.group(1)
        else:
            formatted_date = parse_date(email_to_sync.get('publish_date')).strftime('%Y-%m-%d')
        
        processed_body = process_html_body(original_body)
        
        frontmatter = f"""---
title: "{final_title}"
permalink: "{permalink}"
description: "{description}"
date: {formatted_date}
---

"""
        final_content = frontmatter + processed_body
        
        day_name_for_saving = parse_date(formatted_date).strftime('%A')
        output_dir = SYNC_PATH / day_name_for_saving
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"{slug}.md"
        try:
            output_file.write_text(final_content, encoding='utf-8')
            print(f"  > Successfully saved file to: {output_file}")
        except Exception as e:
            print(f"  > ERROR: Could not write file. {e}")

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

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
                
                payload = { 
                    "subject": subject, 
                    "body": f"Content for {subject} goes here.", 
                    "status": "draft",
                    "email_type": "premium"
                }

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
        
        payload = { 
            "subject": subject, 
            "body": f"Content for {subject} goes here.", 
            "status": "draft",
            "email_type": "premium"
        }

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
    if today.weekday() not in [5, 6]:
        print("This feature is designed to be run on a Saturday or Sunday.")
        return

    load_dotenv()
    BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
    SYNC_PATH_STR = os.getenv("SYNC_PATH")

    if not all([BUTTONDOWN_API_KEY, SYNC_PATH_STR]):
        print("\nERROR: BUTTONDOWN_API_KEY or SYNC_PATH not found in .env file.")
        return

    SYNC_PATH = Path(SYNC_PATH_STR).expanduser()
    if not SYNC_PATH.is_dir():
        print(f"\nERROR: SYNC_PATH '{SYNC_PATH_STR}' is not a valid directory.")
        return

    headers = {"Authorization": f"Token {BUTTONDOWN_API_KEY}"}
    start_of_week = today - timedelta(days=today.weekday())

    url = f"https://api.buttondown.email/v1/emails?email_type=premium&publish_date__start={start_of_week.strftime('%Y-%m-%d')}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        api_emails = response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        print(f"  - ERROR fetching weekly emails for validation: {e}")
        return

    if today.weekday() == 5:
        print(" > It's Saturday. Checking if all weekly posts are synced before creating digest...")
        all_synced = True
        for i in range(6):
            day_to_check = start_of_week + timedelta(days=i)
            day_name = day_to_check.strftime('%A')
            date_str = day_to_check.strftime('%Y-%m-%d')

            email_for_day = next((e for e in api_emails if day_name in e.get('subject', '') and date_str in e.get('subject', '')), None)

            if not email_for_day:
                print(f"  - MISSING: No email published for {day_name}.")
                all_synced = False
                break
            else:
                slug = email_for_day.get('slug')
                day_directory = SYNC_PATH / day_name
                expected_file = day_directory / f"{slug}.md"
                if not expected_file.exists():
                    print(f"  - MISSING: Local file for {day_name} ('{slug}.md') not found.")
                    all_synced = False
                    break
        
        if not all_synced:
            print("\nCannot create digest. Not all posts for the week have been synced locally.")
            return
        else:
            print(" > All weekly posts are synced. Proceeding with digest creation.")

    last_monday = today - timedelta(days=today.weekday())
    last_saturday = last_monday + timedelta(days=5)
    
    url = f"https://api.buttondown.email/v1/emails?email_type=premium&publish_date__start={last_monday.strftime('%Y-%m-%d')}&publish_date__end={last_saturday.strftime('%Y-%m-%d')}"
    
    try:
        print("\n > Fetching posts from the past week...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        weekly_emails = sorted(response.json()['results'], key=lambda x: x['publish_date'])
        
        digest_content_parts = []
        for email in weekly_emails:
            cleaned_body = process_html_body(email['body'])
            digest_content_parts.append(f"## {email['subject']}\n\n{cleaned_body}")
        
        digest_content = "\n\n---\n\n".join(digest_content_parts)

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
            parts = re.split(r'# #OpenToWork Weekly', last_sunday_body)
            if len(parts) > 1:
                open_to_work_content = "# #OpenToWork Weekly" + parts[1]
                print("  - Successfully extracted #OpenToWork Weekly section.")
            else:
                print("  - WARNING: Could not find '# #OpenToWork Weekly' heading in last Sunday's email.")
        else:
            print("  - WARNING: Could not find last Sunday's email.")

    except requests.exceptions.RequestException as e:
        print(f"  - ERROR fetching last Sunday's email: {e}")

    new_subject = f"🌶️ Hot Fudge Sunday for {today.strftime('%Y-%m-%d')}"
    
    new_body_parts = [
        "## Last Week",
        "A look at the week behind...",
        "## This Week",
        "A look at the week ahead...",
        digest_content,
        open_to_work_content if open_to_work_content else "# #OpenToWork Weekly\n\nPlaceholder for open to work section."
    ]
    new_body = "\n\n".join(new_body_parts)
    
    print(f"\n > Creating new digest email: '{new_subject}'")
    
    payload = {
        "subject": new_subject,
        "body": new_body,
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
        print("  4. Sync missing emails from this week")
        print("  5. Create skeleton email(s)")
        print("  6. Create Hot Fudge Sunday digest (Sat/Sun)")
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