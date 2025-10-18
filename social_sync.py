import os
import requests
import frontmatter
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path
import re
from markdownify import markdownify as md
from urllib.parse import urljoin
import markdown # <-- Import the markdown library

# --- Load Environment Variables ---
load_dotenv()
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
SYNC_PATH_STR = os.getenv("SYNC_PATH")
SITE_BASE_URL = os.getenv("SITE_BASE_URL")

# LinkedIn Credentials
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_AUTHOR = os.getenv("LINKEDIN_AUTHOR") 

# GoToSocial Credentials
GOTOSOCIAL_INSTANCE_URL = os.getenv("GOTOSOCIAL_INSTANCE_URL")
GOTOSOCIAL_ACCESS_TOKEN = os.getenv("GOTOSOCIAL_ACCESS_TOKEN")

# --- Verification ---
if not all([BUTTONDOWN_API_KEY, SYNC_PATH_STR, SITE_BASE_URL]):
    raise ValueError("One or more required environment variables are missing in your .env file.")

# --- File & URL Functions ---

def find_recent_markdown_files(directory_path, days=7):
    if not directory_path:
        print("ERROR: SYNC_PATH is not set in your .env file.")
        return []

    sync_path = Path(directory_path).expanduser()
    if not sync_path.is_dir():
        print(f"ERROR: The SYNC_PATH '{sync_path}' is not a valid directory.")
        return []

    recent_files = []
    time_threshold = datetime.now() - timedelta(days=days)

    for file_path in sync_path.rglob("*.md"):
        if "hot-fudge-daily" in file_path.as_posix():
            try:
                modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if modified_time > time_threshold:
                    recent_files.append(file_path)
            except FileNotFoundError:
                continue

    recent_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return recent_files

def check_url_status(url):
    """Checks if a URL is live and returns a 200 status code."""
    try:
        print(f"Checking URL: {url}")
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            print("✅ URL is live.")
            return True
        else:
            print(f"⚠️ URL returned status code {response.status_code}.")
            return False
    except requests.RequestException as e:
        print(f"❌ Could not connect to URL: {e}")
        return False

# --- Buttondown Functions ---

def post_to_buttondown(subject, html_body): # <-- UPDATED to accept html_body
    """Posts content to Buttondown as a draft email."""
    print("\n--- 📮 Posting to Buttondown... ---")
    if not BUTTONDOWN_API_KEY:
        print("❌ BUTTONDOWN_API_KEY not found.")
        return

    headers = {"Authorization": f"Token {BUTTONDOWN_API_KEY}", "Content-Type": "application/json"}
    url = "https://api.buttondown.email/v1/emails"
    # The payload now directly uses the provided HTML body
    payload = {"subject": subject, "body": html_body, "status": "draft", "email_type": "premium"}

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            print(f"✅ Successfully created draft in Buttondown.")
        else:
            print(f"❌ Failed to create draft. Status: {response.status_code}\n   Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")

# --- LinkedIn Functions ---

def format_for_linkedin(subject, description, markdown_content, url):
    """Converts markdown content to a LinkedIn-friendly plain text format."""
    # Convert markdown to plain text by first converting to HTML, then stripping tags
    html = markdown.markdown(markdown_content)
    text = ''.join(re.findall(r'<p>(.*?)</p>', html, re.DOTALL)) # extract text from p tags
    text = re.sub(r'<[^>]+>', '', text) # strip any remaining tags
    text = text.replace('\n', ' ').strip() # clean up newlines
    
    # Re-introduce paragraph breaks for readability
    paragraphs = markdown_content.split('\n\n')
    text = '\n\n'.join(paragraphs)

    return f"{subject}\n\n{description}\n\n{text}\n\nRead the full post here: {url}"


def post_to_linkedin(post_content):
    """Posts the given content to LinkedIn."""
    print("\n--- 🔗 Posting to LinkedIn... ---")
    if not all([LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR]):
        print("❌ LinkedIn credentials not found in .env file.")
        return

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
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    try:
        response = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=post_data)
        response.raise_for_status()
        print("✅ Successfully posted to LinkedIn!")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error posting to LinkedIn: {e}\n   Response: {e.response.text}")

# --- GoToSocial Functions ---

def format_for_gotosocial(subject, markdown_content, url):
    """Converts markdown content to a GoToSocial-friendly plain text format."""
    # This logic can be simplified as GoToSocial handles plain text with newlines well
    paragraphs = markdown_content.split('\n\n')
    text = '\n\n'.join(paragraphs)
    return f"{subject}\n\n{text}\n\nRead the full post here: {url}"


def post_to_gotosocial(post_content):
    """Posts the given content to GoToSocial."""
    print("\n--- 🐘 Posting to GoToSocial... ---")
    if not all([GOTOSOCIAL_INSTANCE_URL, GOTOSOCIAL_ACCESS_TOKEN]):
        print("❌ GoToSocial credentials not found in .env file.")
        return

    headers = {"Authorization": f"Bearer {GOTOSOCIAL_ACCESS_TOKEN}", "Content-Type": "application/json"}
    post_url = f"{GOTOSOCIAL_INSTANCE_URL}/api/v1/statuses"
    post_data = {"status": post_content, "visibility": "public"}

    try:
        response = requests.post(post_url, headers=headers, json=post_data)
        response.raise_for_status()
        print("✅ Successfully posted to GoToSocial!")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error posting to GoToSocial: {e}\n   Response: {e.response.text}")


# --- Main Execution ---

def main():
    """Main function to orchestrate the publishing workflow."""
    print("--- Unified Social Publishing Sync ---")
    recent_files = find_recent_markdown_files(SYNC_PATH_STR)

    if not recent_files:
        print("No recent markdown files found in 'hot-fudge-daily' to sync.")
        return

    print("\n--- Recent Markdown Files (Last 7 Days) ---")
    for i, file_path in enumerate(recent_files):
        print(f"  {i + 1}. {file_path.name}")
    print("-" * 30)

    try:
        choice = input("Enter the number of the file to publish: ").strip()
        index = int(choice) - 1
        if not (0 <= index < len(recent_files)):
            raise ValueError("Invalid number.")
        file_to_post = recent_files[index]
    except (ValueError, IndexError):
        print("❌ Invalid selection. Exiting.")
        return

    # --- Load Post and Verify URL ---
    try:
        post = frontmatter.load(file_to_post)
        subject = post.metadata.get('title', 'No Subject')
        description = post.metadata.get('description', '')
        permalink = post.metadata.get('permalink', '')
        markdown_content = post.content # Renamed for clarity

        if not permalink:
            print("❌ 'permalink' not found in frontmatter. Cannot verify URL.")
            return

        full_url = urljoin(SITE_BASE_URL, permalink)

        if not check_url_status(full_url):
            print("Post is not live yet. Please deploy your site and try again.")
            return

    except Exception as e:
        print(f"Error reading or parsing the markdown file {file_to_post}: {e}")
        return

    # --- Platform Selection ---
    print("\nWhich platforms do you want to post to?")
    print("  1. Buttondown")
    print("  2. LinkedIn")
    print("  3. GoToSocial")
    print("  4. All of the above")
    platform_choice = input("Enter your choice (e.g., '1,3' or '4'): ").strip().lower()

    if not platform_choice:
        print("No platforms selected. Exiting.")
        return

    # --- Process Each Platform Choice with Confirmation ---
    do_buttondown = '1' in platform_choice or '4' in platform_choice
    do_linkedin = '2' in platform_choice or '4' in platform_choice
    do_gotosocial = '3' in platform_choice or '4' in platform_choice

    if do_buttondown:
        # Convert Markdown to HTML for Buttondown
        html_for_buttondown = markdown.markdown(markdown_content, extensions=['fenced_code'])
        print("\n" + "="*50)
        print("                DRY RUN for Buttondown")
        print("This will be created as a DRAFT in Buttondown:")
        print("NOTE: Body will be sent as HTML to preserve formatting.")
        print("="*50 + "\n")
        print(f"Subject: {subject}")
        print(f"Body (first 200 chars of source): {markdown_content.strip()[:200]}...")
        print("\n" + "="*50)
        publish_choice = input(f"Do you want to create this draft in Buttondown? (y/N): ").lower()
        if publish_choice == 'y':
            post_to_buttondown(subject, html_for_buttondown)
        else:
            print("\nPublishing to Buttondown cancelled.")

    if do_linkedin:
        linkedin_post = format_for_linkedin(subject, description, markdown_content, full_url)
        print("\n" + "="*50)
        print("                DRY RUN for LinkedIn")
        print("This will be posted to LinkedIn:")
        print("="*50 + "\n")
        print(linkedin_post)
        print("\n" + "="*50)
        publish_choice = input(f"Do you want to publish this to LinkedIn? (y/N): ").lower()
        if publish_choice == 'y':
            post_to_linkedin(linkedin_post)
        else:
            print("\nPublishing to LinkedIn cancelled.")

    if do_gotosocial:
        gotosocial_post = format_for_gotosocial(subject, markdown_content, full_url)
        print("\n" + "="*50)
        print("                DRY RUN for GoToSocial")
        print("This will be posted to GoToSocial:")
        print("="*50 + "\n")
        print(gotosocial_post)
        print("\n" + "="*50)
        publish_choice = input(f"Do you want to publish this to GoToSocial? (y/N): ").lower()
        if publish_choice == 'y':
            post_to_gotosocial(gotosocial_post)
        else:
            print("\nPublishing to GoToSocial cancelled.")

    print("\n--- Sync Complete ---")

if __name__ == "__main__":
    main()