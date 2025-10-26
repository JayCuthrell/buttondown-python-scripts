import os
import requests
import frontmatter
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path
import re
from urllib.parse import urljoin

# --- Load Environment Variables ---
load_dotenv()
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
BUTTONDOWN_EDIT = os.getenv("BUTTONDOWN_EDIT")
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

def post_to_buttondown(subject, body_content):
    """Posts content to Buttondown as a draft email."""
    print("\n--- 📮 Posting to Buttondown... ---")
    if not BUTTONDOWN_API_KEY:
        print("❌ BUTTONDOWN_API_KEY not found.")
        return

    headers = {"Authorization": f"Token {BUTTONDOWN_API_KEY}", "Content-Type": "application/json"}
    url = "https://api.buttondown.email/v1/emails"
    editor_mode_comment = f"{BUTTONDOWN_EDIT}"
    final_body = f"{editor_mode_comment}{body_content}"
    payload = {"subject": subject, "body": final_body, "status": "draft", "email_type": "premium"}

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            print(f"✅ Successfully created draft in Buttondown.")
        else:
            print(f"❌ Failed to create draft. Status: {response.status_code}\n   Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")

# --- LinkedIn Functions ---

# --- UPDATED: Advanced LinkedIn Formatting Function ---
def format_for_linkedin(subject, description, markdown_content, url):
    """
    Converts markdown to a LinkedIn-friendly plain text format with footnotes.
    This function contains the advanced formatting logic.
    """
    footnotes = []
    
    # --- FIX 1: Check for and remove repeated description ---
    text = markdown_content
    if description and text.lstrip().startswith(description):
        # Remove the description text and any following newlines
        text = text.lstrip()[len(description):].lstrip('\n')

    def link_to_footnote(match):
        link_text = match.group(1) # Group 1 is [text]
        link_url = match.group(2)  # Group 2 is (url)
        if link_text.startswith('!') or not link_url.startswith('http'):
            return f"[{link_text}]({link_url})" # Ignore images or relative links
        footnotes.append(link_url)
        return f"{link_text} [{len(footnotes)}]"

    def convert_md_table_to_list(match):
        table_text = match.group(0)
        lines = table_text.strip().split('\n')
        if len(lines) < 3: return table_text
        list_items = []
        for row in lines[2:]:
            columns = [col.strip() for col in row.split('|') if col.strip()]
            if len(columns) >= 2:
                list_items.append(f"• {' - '.join(columns)}")
        return "\n".join(list_items) if list_items else ""

    text = text.replace('\\*', '*').replace('\\$', '$').replace('\\_', '_')
    text = re.sub(r'\{\{.*?\}\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'^\s*---\s*$', '', text, flags=re.MULTILINE)
    
    table_pattern = re.compile(r'^\s*\|.*\|.*\n\s*\|[-|: ]+\|.*\n((?:\s*\|.*\|.*\n?)+)', re.MULTILINE)
    text = table_pattern.sub(convert_md_table_to_list, text)
    
    # --- FIX 2: More robust regex for links. Handles ')' in link text. ---
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link_to_footnote, text)
    
    # Clean up daily-themed headings (adjust patterns as needed)
    text = re.sub(r'#+\s*📈\s*Markets Monday.*', '📈 Markets Monday', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🔥\s*Hot Takes Tuesday.*', '🔥 Hot Takes Tuesday', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🤪\s*Wacky Wednesday.*', '🤪 Wacky Wednesday', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🔙\s*Throwback Thursday.*', '🔙 Throwback Thursday', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*✅\s*Final Thoughts Friday.*', '✅ Final Thoughts Friday', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🔮\s*Sneak Peak Saturday.*', '🔮 Sneak Peak Saturday', text, flags=re.IGNORECASE)

    # --- FIX 3: Better heading formatting to add spacing (from linkedin_sync.py) ---
    text = re.sub(r'^#+\s*(.+)$', r'\n\n\1\n', text, flags=re.MULTILINE)
    
    text = re.sub(r'([\.!\?])\s*([A-Z])', r'\1\n\n\2', text) # Add paragraph breaks
    text = re.sub(r'(\*\*|__)', '', text) # Remove bold/italic
    
    # --- FIX 4: Convert bullet points (this should work correctly now) ---
    text = re.sub(r'^\s*[\*\-]\s*', '• ', text, flags=re.MULTILINE)
    
    text = re.sub(r'\n{3,}', '\n\n', text).strip() # Clean up extra newlines

    footnote_section = ""
    if footnotes:
        footnote_lines = [f"[{i+1}] {url}" for i, url in enumerate(footnotes)]
        footnote_section = "\n\n---\nSources:\n" + "\n".join(footnote_lines)
    
    return f"{subject}\n\n{description}\n\n{text}{footnote_section}\n\nRead the full post here: {url}"

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

# --- RESTORED: Original simple formatting for GoToSocial ---
def format_for_gotosocial(subject, markdown_content, url):
    """Converts markdown content to a GoToSocial-friendly plain text format."""
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
    # ... (The first part of the main function is unchanged) ...
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

    try:
        post = frontmatter.load(file_to_post)
        subject = post.metadata.get('title', 'No Subject')
        description = post.metadata.get('description', '')
        permalink = post.metadata.get('permalink', '')
        markdown_content = post.content

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

    print("\nWhich platforms do you want to post to?")
    print("  1. Buttondown")
    print("  2. LinkedIn")
    print("  3. GoToSocial")
    print("  4. All of the above")
    platform_choice = input("Enter your choice (e.g., '1,3' or '4'): ").strip().lower()

    if not platform_choice:
        print("No platforms selected. Exiting.")
        return

    do_buttondown = '1' in platform_choice or '4' in platform_choice
    do_linkedin = '2' in platform_choice or '4' in platform_choice
    do_gotosocial = '3' in platform_choice or '4' in platform_choice

    if do_buttondown:
        # ... (Buttondown logic is unchanged) ...
        editor_mode_comment = f"{BUTTONDOWN_EDIT}"
        body_for_buttondown = f"{editor_mode_comment}\n{markdown_content}"
        print("\n" + "="*50)
        print("                DRY RUN for Buttondown")
        print("="*50 + "\n")
        print(f"Subject: {subject}")
        print(f"Body (first 200 chars): {body_for_buttondown.strip()[:200]}...")
        print("\n" + "="*50)
        publish_choice = input(f"Do you want to create this draft in Buttondown? (y/N): ").lower()
        if publish_choice == 'y':
            post_to_buttondown(subject, body_for_buttondown)
        else:
            print("\nPublishing to Buttondown cancelled.")

    if do_linkedin:
        # --- CORRECTED: Call the new, specific LinkedIn formatter ---
        linkedin_post = format_for_linkedin(subject, description, markdown_content, full_url)
        print("\n" + "="*50)
        print("                DRY RUN for LinkedIn")
        print("="*50 + "\n")
        print(linkedin_post)
        print("\n" + "="*50)
        publish_choice = input(f"Do you want to publish this to LinkedIn? (y/N): ").lower()
        if publish_choice == 'y':
            post_to_linkedin(linkedin_post)
        else:
            print("\nPublishing to LinkedIn cancelled.")

    if do_gotosocial:
        # --- CORRECTED: Call the original, simple GoToSocial formatter ---
        gotosocial_post = format_for_gotosocial(subject, markdown_content, full_url)
        print("\n" + "="*50)
        print("                DRY RUN for GoToSocial")
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
