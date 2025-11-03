import os
import requests
import json
import re
from dotenv import load_dotenv
from mimetypes import guess_type

# Load env variables
load_dotenv()
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_AUTHOR = os.getenv("LINKEDIN_AUTHOR")

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

# --- NEW: Post to LinkedIn Version 1.0

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

# --- NEW: Post to LinkedIn with Media Version 1.0 ---

def format_for_linkedin2(subject, description, markdown_content, url):
    """
    Converts markdown to a LinkedIn-friendly plain text format with footnotes.
    (Using the advanced version provided in the prompt)
    """
    footnotes = []

    # Check for and remove repeated description
    text = markdown_content
    if description and text.lstrip().startswith(description):
        text = text.lstrip()[len(description):].lstrip('\n')

    def link_to_footnote(match):
        link_text = match.group(1) # [text]
        link_url = match.group(2)  # (url)
        # Ignore images or relative links (basic check)
        if link_text.startswith('!') or not link_url.startswith(('http://', 'https://')):
            # Reconstruct the original markdown link/image if it's not an external link
             return f"[{link_text}]({link_url})"
        footnotes.append(link_url)
        return f"{link_text} [{len(footnotes)}]"


    def convert_md_table_to_list(match):
        table_text = match.group(0)
        lines = table_text.strip().split('\n')
        if len(lines) < 3: return table_text # Not a valid table structure
        list_items = []
        # Skip header and separator lines
        for row in lines[2:]:
            # Split by '|' and strip whitespace, filter empty strings
            columns = [col.strip() for col in row.strip('|').split('|') if col.strip()]
            if len(columns) >= 2: # Need at least two columns for a meaningful list item
                list_items.append(f"• {' - '.join(columns)}") # Join columns with ' - '
        return "\n".join(list_items) if list_items else "" # Return joined list or empty string


    text = text.replace('\\*', '*').replace('\\$', '$').replace('\\_', '_')
    # Remove Hugo shortcodes or similar patterns more carefully
    text = re.sub(r'{{<.*? >}}', '', text, flags=re.IGNORECASE | re.DOTALL) # Handle multi-line shortcodes
    text = re.sub(r'```[\s\S]*?```', '', text) # Remove code blocks
    text = re.sub(r'^\s*---\s*$', '', text, flags=re.MULTILINE) # Remove horizontal rules

    # Process tables first
    table_pattern = re.compile(r'^\s*\|.*\|.*\n\s*\|[-|: ]+\|.*\n((?:\s*\|.*\|.*\n?)+)', re.MULTILINE)
    text = table_pattern.sub(convert_md_table_to_list, text)

    # Process links after tables to avoid messing up table formatting
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link_to_footnote, text)

    # Clean up daily-themed headings
    text = re.sub(r'#+\s*📈\s*Markets Monday.*', '📈 Markets Monday', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'#+\s*🔥\s*Hot Takes Tuesday.*', '🔥 Hot Takes Tuesday', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'#+\s*🤪\s*Wacky Wednesday.*', '🤪 Wacky Wednesday', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'#+\s*🔙\s*Throwback Thursday.*', '🔙 Throwback Thursday', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'#+\s*✅\s*Final Thoughts Friday.*', '✅ Final Thoughts Friday', text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r'#+\s*🔮\s*Sneak Peak Saturday.*', '🔮 Sneak Peak Saturday', text, flags=re.IGNORECASE | re.MULTILINE)

    # Convert Markdown headings to plain text with spacing
    text = re.sub(r'^#+\s*(.+)$', r'\n\n\1\n', text, flags=re.MULTILINE)

    # Add paragraph breaks after sentences ending with . ! ? followed by a capital letter
    text = re.sub(r'([\.!\?])\s+(?=[A-Z])', r'\1\n\n', text)

    text = re.sub(r'(\*\*|__)', '', text) # Remove bold/italic markup

    # Convert Markdown list items (* or -) to bullet points (•)
    text = re.sub(r'^\s*[\*\-]\s+', '• ', text, flags=re.MULTILINE)

    # Remove any leftover heading markers (should be redundant if heading conversion worked)
    # text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)

    # Consolidate multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    footnote_section = ""
    if footnotes:
        footnote_lines = [f"[{i+1}] {url}" for i, url in enumerate(footnotes)]
        footnote_section = "\n\n---\nSources:\n" + "\n".join(footnote_lines)

    # Final assembly
    return f"{subject}\n\n{description}\n\n{text}{footnote_section}\n\nRead the full post here: {url}"


def post_to_linkedin2(post_content):
    """Posts TEXT-ONLY content to LinkedIn."""
    print("\n--- 🔗 Posting to LinkedIn (Text-Only)... ---")
    if not all([LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR]):
        print("❌ LinkedIn credentials (LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR) not found in .env file.")
        return False # Indicate failure

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
        print("✅ Successfully posted text to LinkedIn!")
        return True # Indicate success
    except requests.exceptions.RequestException as e:
        print(f"❌ Error posting text to LinkedIn: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"   Response: {e.response.text}")
        return False # Indicate failure

# --- NEW: Function to post WITH media ---
def post_to_linkedin_with_media(post_content, media_filename, subject):
    """
    Posts content with an image/GIF to LinkedIn.
    """
    print(f"\n--- 🔗 Posting to LinkedIn (With Media: {media_filename})... ---")
    if not all([LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR]):
        print("❌ LinkedIn credentials (LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR) not found in .env file.")
        return False # Indicate failure

    # === 1. Register the Upload ===
    print("  1. Registering media upload...")
    register_headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    register_data = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"], # Use "feedshare-image" for GIFs too
            "owner": LINKEDIN_AUTHOR,
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }]
        }
    }

    try:
        r_register = requests.post(
            "https://api.linkedin.com/v2/assets?action=registerUpload",
            headers=register_headers,
            json=register_data
        )
        r_register.raise_for_status()
        register_response = r_register.json()

        upload_url = register_response["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = register_response["value"]["asset"]

        print(f"  ✅ Upload URL received. Asset URN: {asset_urn}")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error registering upload: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"   Response: {e.response.text}")
        return False # Indicate failure

    # === 2. Upload the Media File ===
    print(f"  2. Uploading '{media_filename}'...")

    content_type, _ = guess_type(media_filename)
    if not content_type:
        content_type = "image/gif" # Default if guess fails
        print(f"  ⚠️ Could not guess mime type, defaulting to {content_type}")

    upload_headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}", # Needs token for upload too
        "Content-Type": content_type
    }

    try:
        with open(media_filename, 'rb') as f:
            media_data = f.read()

        r_upload = requests.put( # Use PUT for the upload URL
            upload_url,
            headers=upload_headers,
            data=media_data
        )
        r_upload.raise_for_status()
        # LinkedIn upload URL often returns 201 Created on success
        if r_upload.status_code not in [200, 201]:
             print(f"  ⚠️ Media upload returned status {r_upload.status_code}, continuing but post might fail.")
        else:
             print("  ✅ Media file uploaded successfully.")


    except (requests.exceptions.RequestException, IOError) as e:
        print(f"\n❌ Error uploading media: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"   Response: {e.response.text}")
        return False # Indicate failure
    except Exception as e: # Catch other potential errors like file not found
        print(f"\n❌ Unexpected error during media upload: {e}")
        return False


    # === 3. Create the Post with Media ===
    print("  3. Creating the final post...")
    post_headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "x-li-format": "json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    post_data = {
        "author": LINKEDIN_AUTHOR,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_content},
                "shareMediaCategory": "IMAGE", # Use "IMAGE" for GIFs on LinkedIn API v2
                "media": [{
                    "status": "READY",
                    "description": {"text": "Animated post title"}, # Alt text for the media
                    "media": asset_urn,
                    "title": {"text": subject} # Title for the media
                }]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    try:
        r_post = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=post_headers, json=post_data)
        r_post.raise_for_status()
        print("\n✅ Successfully posted to LinkedIn with media!")
        return True # Indicate success
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error creating final post: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"   Response: {e.response.text}")
        return False # Indicate failure
