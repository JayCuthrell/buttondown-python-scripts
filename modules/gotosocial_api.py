import os
import requests
import json
import re
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()
GOTOSOCIAL_INSTANCE_URL = os.getenv("GOTOSOCIAL_INSTANCE_URL")
GOTOSOCIAL_ACCESS_TOKEN = os.getenv("GOTOSOCIAL_ACCESS_TOKEN")

def format_for_gotosocial(subject, markdown_content, url):
    """Converts markdown content to a GoToSocial-friendly plain text format."""
    # Basic conversion: Remove markdown syntax, keep paragraphs
    text = re.sub(r'#+\s*', '', markdown_content) # Remove headings
    text = re.sub(r'(\*\*|__)', '', text)        # Remove bold/italic
    text = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)|!\[.*?\]\(.*?\)', '', text) # Remove images
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text) # Keep link text only
    text = re.sub(r'^\s*[\*\-]\s*', '• ', text, flags=re.MULTILINE) # Basic lists
    text = re.sub(r'\n{3,}', '\n\n', text).strip() # Consolidate newlines
    return f"{subject}\n\n{text}\n\nRead the full post here: {url}"


def post_to_gotosocial(post_content):
    """Posts the given content to GoToSocial."""
    print("\n--- 🐘 Posting to GoToSocial... ---")
    if not all([GOTOSOCIAL_INSTANCE_URL, GOTOSOCIAL_ACCESS_TOKEN]):
        print("❌ GoToSocial credentials not found in .env file.")
        return

    headers = {"Authorization": f"Bearer {GOTOSOCIAL_ACCESS_TOKEN}", "Content-Type": "application/json"}
    post_url = f"{GOTOSOCIAL_INSTANCE_URL.rstrip('/')}/api/v1/statuses" # Ensure no double slash
    post_data = {"status": post_content, "visibility": "public"}

    try:
        response = requests.post(post_url, headers=headers, json=post_data)
        response.raise_for_status()
        print("✅ Successfully posted to GoToSocial!")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error posting to GoToSocial: {e}\n   Response: {response.text}")