import os
import csv
import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from dateutil.parser import parse as parse_date
from datetime import datetime

# --- Helper Functions ---

def _print_content_to_screen(content: str):
    """Helper function to format and print final content to the console."""
    print("\n" + "="*50)
    print("--- FINALIZED MARKDOWN FOR LATEST EMAIL ---")
    print("="*50 + "\n")
    print(content)

def sanitize_title(title: str) -> str:
    """
    Removes emoji and cleans up leading/trailing/multiple whitespace from a string.
    """
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    no_emoji_title = emoji_pattern.sub(r'', title)
    clean_title = " ".join(no_emoji_title.split())
    return clean_title

def _parse_description_from_response(response: requests.Response) -> str | None:
    """Helper to parse description from a successful HTTP response."""
    soup = BeautifulSoup(response.text, 'html.parser')
    meta_tag = soup.find('meta', attrs={'name': 'description'})
    if meta_tag and 'content' in meta_tag.attrs:
        return meta_tag['content'].strip()
    return None

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

def add_missing_alt_tags_from_figcaption(body: str) -> str:
    """Parses HTML to find img tags in figures and uses figcaption text as alt text."""
    soup = BeautifulSoup(body, 'html.parser')
    figures = soup.find_all('figure')
    replacements_made = 0

    for figure in figures:
        img_tag = figure.find('img')
        figcaption_tag = figure.find('figcaption')

        if img_tag and figcaption_tag and not img_tag.has_attr('alt'):
            alt_text = figcaption_tag.get_text(strip=True).replace('"', "'")
            if alt_text:
                img_tag['alt'] = alt_text
                replacements_made += 1

    if replacements_made > 0:
        print(f"  > Fixed {replacements_made} missing alt tag(s) using figcaptions.", flush=True)
        return soup.prettify()
    return body

# --- Main Operating Modes ---

def process_new_export():
    """MODE 1: Processes a new Buttondown export, creating permalinks."""
    print("\n--- Mode: Process New Buttondown Export ---")
    # ... (code remains the same)

def retry_failed_fetches():
    """MODE 2: Retries fetching descriptions for previously failed files."""
    print("\n--- Mode: Retry Failed Descriptions ---")
    # ... (code remains the same)

def fix_alt_tags_in_folder():
    """MODE 3: Scans an import-ready folder and fixes missing alt tags."""
    print("\n--- Mode: Fix Empty Alt Tags ---")
    # ... (code remains the same)

def sync_latest_from_api():
    """MODE 4: Fetches the latest email from the API and prints or saves it."""
    print("\n--- Mode: Sync Latest Email ---")
    
    load_dotenv()
    BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")

    if not BUTTONDOWN_API_KEY:
        print("\nERROR: BUTTONDOWN_API_KEY not found.")
        print("Please create a .env file in the same directory and add your key.")
        return

    headers = {"Authorization": f"Token {BUTTONDOWN_API_KEY}"}
    
    # --- DYNAMIC DATE and UPDATED URL ---
    today_str = datetime.now().strftime('%Y-%m-%d')
    url = f"https://api.buttondown.email/v1/emails?&page=1&publish_date__start={today_str}"
    
    try:
        print(f" > Fetching emails from Buttondown API for today ({today_str})...", flush=True)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        emails = response.json()["results"]
        if not emails:
            print("No emails found for today.")
            return

        latest_email = sorted(emails, key=lambda x: x['publish_date'], reverse=True)[0]
        print(f" > Found latest email: '{latest_email['subject']}'", flush=True)

        raw_subject = latest_email.get('subject', 'No Subject')
        slug = latest_email.get('slug', '')
        
        final_title = raw_subject.replace('"', "'")
        permalink = f"/archive/{slug}/"
        description = get_web_description(slug, raw_subject).replace('"', "'")
        
        publish_date_obj = parse_date(latest_email.get('publish_date'))
        formatted_date = publish_date_obj.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + '+00:00'
        
        original_body = latest_email.get('body', '')
        processed_body = add_missing_alt_tags_from_figcaption(original_body)
        
        frontmatter = f"""---
title: "{final_title}"
permalink: "{permalink}"
description: "{description}"
date: {formatted_date}
---

"""
        final_content = frontmatter + processed_body

        output_dir_str = input("\nEnter a directory path to save the file (or press Enter to print to screen): ").strip()

        if output_dir_str:
            output_dir = Path(output_dir_str).expanduser()
            if output_dir.is_dir():
                output_file = output_dir / f"{slug}.md"
                try:
                    output_file.write_text(final_content, encoding='utf-8')
                    print(f"\nSuccessfully saved file to: {output_file}")
                except Exception as e:
                    print(f"\nERROR: Could not write file. {e}")
            else:
                print(f"\nERROR: '{output_dir_str}' is not a valid directory. Printing to screen instead.")
                _print_content_to_screen(final_content)
        else:
            _print_content_to_screen(final_content)

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
    except (KeyError, IndexError):
        print("Could not find expected data in API response.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def main():
    """Main function to display the menu and run the selected mode."""
    print("--- Buttondown to Eleventy Email Processor ---")
    
    while True:
        print("\nWhat would you like to do?")
        print("  1. Process new export (creates permalinks, keeps emoji in titles)")
        print("  2. Retry failed descriptions in an 'emails_ready_for_import' folder")
        print("  3. Fix empty alt tags in an 'emails_ready_for_import' folder")
        print("  4. Sync latest email and save to file (via API)")
        print("  5. Exit")
        choice = input("Enter your choice (1, 2, 3, 4, or 5): ")

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
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please select a valid option.")

if __name__ == "__main__":
    main()