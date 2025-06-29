import os
import csv
import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup

def sanitize_title(title: str) -> str:
    """
    Removes emoji and cleans up leading/trailing/multiple whitespace from a string.
    NOTE: This function is no longer used for the main title as of the permalink update,
          but is kept for potential future use.
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

def get_web_description(slug: str, raw_title: str) -> str:
    """
    Fetches the meta description for a given slug. If the primary URL 404s,
    it constructs and tries a fallback URL from the raw_title.
    """
    primary_url = f"https://hot.fudge.org/archive/{slug}"
    print(f"  > Trying primary URL: {primary_url}")

    try:
        response = requests.get(primary_url, timeout=15)
        response.raise_for_status()
        description = _parse_description_from_response(response)
        if description:
            return description
        else:
            print("  > WARNING: Meta description not found on page.")
            return "No description available."
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"  > Primary URL not found (404).")
            fallback_slug = raw_title.lower().replace(' ', '-')
            fallback_url = f"https://hot.fudge.org/archive/{fallback_slug}"
            print(f"  > Trying fallback URL with original title: {fallback_url}")

            try:
                fallback_response = requests.get(fallback_url, timeout=15)
                fallback_response.raise_for_status()
                description = _parse_description_from_response(fallback_response)
                if description:
                    return description
                else:
                    print("  > WARNING: Meta description not found on fallback page.")
                    return "No description available."
            except requests.exceptions.RequestException as fallback_e:
                print(f"  > ERROR: Fallback failed. {fallback_e}")
                return "Error fetching description."
        else:
            print(f"  > ERROR: Primary request failed. {e}")
            return "Error fetching description."
    except requests.exceptions.RequestException as e:
        print(f"  > ERROR: Primary request failed. {e}")
        return "Error fetching description."

def add_missing_alt_tags_from_figcaption(body: str) -> str:
    """
    Parses HTML to find img tags in figures and uses figcaption text as alt text.
    """
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
        print(f"  > Fixed {replacements_made} missing alt tag(s) using figcaptions.")
        return str(soup)
    return body


def process_new_export():
    """
    MODE 1: Processes a new Buttondown export, creating permalinks and keeping original titles.
    """
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
                
                # --- New Logic for Title and Permalink ---
                raw_subject = row.get('subject', 'No Subject')
                
                # Title is the original subject, with quotes sanitized
                final_title = raw_subject.replace('"', "'")
                
                # Permalink is generated from the clean slug in the CSV
                permalink = f"/archive/{slug}/"
                
                description = get_web_description(slug, raw_subject).replace('"', "'")
                
                source_md_path = emails_folder_path / f"{slug}.md"
                if not source_md_path.is_file():
                    print(f"  > ERROR: Markdown file not found at {source_md_path}. Skipping.")
                    continue
                
                original_body = source_md_path.read_text(encoding='utf-8')
                processed_body = add_missing_alt_tags_from_figcaption(original_body)
                
                # --- Updated Frontmatter Structure ---
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
    """
    MODE 2: Retries fetching descriptions for previously failed files.
    """
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
    """
    MODE 3: Scans an import-ready folder and fixes missing alt tags in place using figcaptions.
    """
    print("\n--- Mode: Fix Empty Alt Tags ---")
    import_dir_str = input("Enter the path to the 'emails_ready_for_import' directory: ")
    import_dir = Path(import_dir_str).expanduser()
    if not import_dir.is_dir():
        print(f"\nERROR: The directory '{import_dir}' does not exist.")
        return

    print(f"\nScanning for missing alt tags in: {import_dir}")
    updated_files_count = 0
    
    for md_file in import_dir.glob("*.md"):
        original_content = md_file.read_text(encoding='utf-8')
        modified_content = add_missing_alt_tags_from_figcaption(original_content)
        
        if modified_content != original_content:
            print(f"Checking: {md_file.name}")
            md_file.write_text(modified_content, encoding='utf-8')
            updated_files_count += 1
            print(f"  > UPDATED: {md_file.name}")

    print("\n--- Alt Tag Fix Complete! ---")
    if updated_files_count > 0:
        print(f"Successfully updated {updated_files_count} file(s).")
    else:
        print("No files needed fixing.")

def main():
    """
    Main function to display the menu and run the selected mode.
    """
    print("--- Buttondown to Eleventy Email Processor ---")
    
    while True:
        print("\nWhat would you like to do?")
        print("  1. Process new export (creates permalinks, keeps emoji in titles)")
        print("  2. Retry failed descriptions in an 'emails_ready_for_import' folder")
        print("  3. Fix empty alt tags in an 'emails_ready_for_import' folder")
        print("  4. Exit")
        choice = input("Enter your choice (1, 2, 3, or 4): ")

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
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()