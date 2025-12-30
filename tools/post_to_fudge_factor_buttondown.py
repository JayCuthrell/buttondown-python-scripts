import os
import requests
import frontmatter
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path

# --- Load Environment Variables ---
load_dotenv()
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
SYNC_PATH_STR = os.getenv("SYNC_PATH")


def find_recent_markdown_files(directory_path, days=7):
    """
    Finds all markdown files in the 'fudge-factor' subdirectory that have
    been modified within a given number of days.
    """
    if not directory_path:
        print("ERROR: SYNC_PATH is not set in your .env file.")
        return []

    sync_path = Path(directory_path).expanduser()
    if not sync_path.is_dir():
        print(f"ERROR: The SYNC_PATH '{sync_path}' is not a valid directory.")
        return []

    recent_files = []
    time_threshold = datetime.now() - timedelta(days=days)

    # Use rglob to find all markdown files recursively
    for file_path in sync_path.rglob("*.md"):
        #
        # --- IMPROVEMENT IS HERE ---
        # Ensure the file is within a 'fudge-factor' directory structure
        if "fudge-factor" in file_path.as_posix():
            try:
                modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if modified_time > time_threshold:
                    recent_files.append(file_path)
            except FileNotFoundError:
                continue

    # Sort files by modification time, newest first
    recent_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return recent_files


def post_to_buttondown(file_path):
    """
    Reads a markdown file and posts its content to Buttondown as a draft email.
    """
    if not BUTTONDOWN_API_KEY:
        raise ValueError("BUTTONDOWN_API_KEY not found in environment variables.")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            subject = post.metadata.get('title', 'No Subject')
            content_body = post.content
            permalink = post.metadata.get('permalink', '')
    except Exception as e:
        print(f"Error reading or parsing the markdown file {file_path}: {e}")
        return False

    editor_mode_comment = "<!-- buttondown-editor-mode: plaintext -->"
    final_body = f"{editor_mode_comment}{content_body}"

    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
        "Content-Type": "application/json"
    }
    url = "https://api.buttondown.email/v1/emails"
    payload = {"subject": subject, "body": final_body, "status": "draft", "email_type": "public", "canonical_url": "https://fudge.org" + permalink}

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            print(f"✅ Successfully created draft for: '{subject}'")
            return True
        else:
            print(f"❌ Failed to create draft for '{subject}'. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        return False


def main():
    """
    Main function to find recent posts and prompt the user for which to sync.
    """
    if "GITHUB_ACTIONS" in os.environ and len(sys.argv) > 1:
        file_path_arg = sys.argv[1]
        print(f"GitHub Action detected. Processing file: {file_path_arg}")
        if "fudge-factor" in str(file_path_arg) and str(file_path_arg).endswith(".md"):
            post_to_buttondown(file_path_arg)
        else:
            print("File is not in the 'fudge-factor' directory or is not a markdown file. Skipping.")
        return

    print("--- Interactive Buttondown Post Sync ---")
    recent_files = find_recent_markdown_files(SYNC_PATH_STR)

    if not recent_files:
        print("No recent markdown files found in 'fudge-factor' to sync.")
        return

    print("\n--- Recent Markdown Files in 'fudge-factor' (Last 7 Days) ---")
    for i, file_path in enumerate(recent_files):
        print(f"  {i + 1}. {file_path.name}")
    print("-" * 30)

    choice = input("Enter the number of the file to post (or 'all', or press Enter to cancel): ").strip().lower()

    if not choice:
        print("Operation cancelled.")
        return

    files_to_post = []
    if choice == 'all':
        files_to_post = recent_files
    elif choice.isdigit():
        try:
            index = int(choice) - 1
            if 0 <= index < len(recent_files):
                files_to_post.append(recent_files[index])
            else:
                print("❌ Invalid number.")
                return
        except (ValueError, IndexError):
            print("❌ Invalid selection.")
            return
    else:
        print("❌ Invalid input.")
        return

    print("\n" + "="*50)
    print("This will create drafts in Buttondown for:")
    for file_path in files_to_post:
        print(f"  - {file_path.name}")
    print("="*50 + "\n")

    publish_choice = input("Do you want to proceed? (y/N): ").lower()
    if publish_choice == 'y':
        print("\nSending to Buttondown...")
        success_count = 0
        for file_path in files_to_post:
            if post_to_buttondown(file_path):
                success_count += 1
        print(f"\nSync complete. Successfully posted {success_count} of {len(files_to_post)} file(s).")
    else:
        print("\nPublishing cancelled.")


if __name__ == "__main__":
    main()