import os
import requests
import frontmatter
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path
import re
from urllib.parse import urljoin
import glob # --- NEW ---
from mimetypes import guess_type # --- NEW ---

# --- NEW: Import Pillow components ---
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: The 'Pillow' library is required. Please install it using: pip install Pillow")
    sys.exit(1)

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
# Modified to check for LinkedIn creds only if needed later
if not all([BUTTONDOWN_API_KEY, SYNC_PATH_STR, SITE_BASE_URL]):
    raise ValueError("One or more required environment variables are missing (BUTTONDOWN_API_KEY, SYNC_PATH, SITE_BASE_URL).")

# --- File & URL Functions ---

def find_recent_markdown_files(directory_path, days=7):
    """
    Finds markdown files in the specified directory modified within the last `days`.
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

    # Simplified: search directly in the SYNC_PATH, assuming it points to the correct place
    for file_path in sync_path.rglob("*.md"):
        # You might want to add more specific path filtering if SYNC_PATH is broad
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
    editor_mode_comment = f"{BUTTONDOWN_EDIT}" if BUTTONDOWN_EDIT else "" # Default if not set
    final_body = f"{editor_mode_comment}\n{body_content}" # Added newline for clarity
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

def format_for_linkedin(subject, description, markdown_content, url):
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


def post_to_linkedin(post_content):
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

# --- NEW: Function from linkedin_sync_gif.py to post WITH media ---
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


# --- GoToSocial Functions ---

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

# --- NEW: GIF Creation Functions (from linkedin_sync_gif.py) ---

def is_emoji(char):
    """Checks if a character is in a common emoji Unicode range."""
    # Ranges covering common emojis including those used in the script
    if '\U0001F300' <= char <= '\U0001F5FF': return True # Misc Symbols/Pictographs
    if '\U0001F600' <= char <= '\U0001F64F': return True # Emoticons
    if '\U0001F900' <= char <= '\U0001F9FF': return True # Supplemental Symbols
    if '\u2600' <= char <= '\u27BF': return True # Misc Symbols (includes ✅)
    if '\U0001FA70' <= char <= '\U0001FAFF': return True # Symbols and Pictographs Extended-A
    # Add more ranges if needed
    return False

def find_font(glob_pattern, name_for_log=""):
    """Finds a single font file matching a glob pattern across common system dirs."""
    if not name_for_log: name_for_log = glob_pattern

    # Prioritize specific known paths, especially for system fonts like Apple Emoji
    if glob_pattern == 'Apple Color Emoji.ttc':
        apple_path = '/System/Library/Fonts/Apple Color Emoji.ttc'
        if Path(apple_path).is_file():
            print(f"✅ Found {name_for_log} font at: {apple_path} (Hardcoded path)")
            return apple_path
        # If not found, fall through to search other dirs

    font_dirs_to_search = [
        os.path.expanduser('~/Library/Fonts/'), # Mac User
        '/Library/Fonts/',                      # Mac System
        '/System/Library/Fonts/',               # Mac System
        '/System/Library/Fonts/Core/',          # Mac System (alternate)
        '/usr/share/fonts/',                    # Linux Common
        '/usr/local/share/fonts/',              # Linux Local
        os.path.expanduser('~/.fonts/'),        # Linux User
        'C:\\Windows\\Fonts\\'                  # Windows
    ]

    all_found_fonts = []
    for font_dir in font_dirs_to_search:
        if not Path(font_dir).is_dir(): continue # Skip if dir doesn't exist
        # Use recursive glob (**) to find files in subdirectories
        search_path = os.path.join(font_dir, '**', glob_pattern)
        try:
            # Use Path.glob for better compatibility and handling
            found = list(Path(font_dir).glob(f'**/{glob_pattern}'))
            if found:
                all_found_fonts.extend(str(p) for p in found) # Convert Path objects to strings
        except Exception as e:
            print(f"  ⚠️ Error searching in {font_dir}: {e}") # Log errors during search

    if all_found_fonts:
        all_found_fonts.sort() # Sort for consistency

        # Prioritize Noto Sans Regular if searching for it
        if 'Noto*Sans*Regular' in glob_pattern:
            for f in all_found_fonts:
                if f.endswith('NotoSans-Regular.ttf'):
                    print(f"✅ Found {name_for_log} font at: {f} (Prioritized)")
                    return f
            # If specific regular not found, try any Noto Sans Regular variant
            for f in all_found_fonts:
                 if 'NotoSans' in f and 'Regular' in f and f.endswith('.ttf'):
                      print(f"✅ Found {name_for_log} font at: {f} (Prioritized Variant)")
                      return f

        # Prioritize Noto Color Emoji if searching for it
        if 'Noto*Color*Emoji' in glob_pattern:
            for f in all_found_fonts:
                if 'NotoColorEmoji.ttf' in f: # Exact match preferred
                    print(f"✅ Found {name_for_log} font at: {f} (Prioritized)")
                    return f
            # Fallback to any Noto Color Emoji variant
            for f in all_found_fonts:
                 if 'Noto' in f and 'Color' in f and 'Emoji' in f and f.endswith('.ttf'):
                      print(f"✅ Found {name_for_log} font at: {f} (Prioritized Variant)")
                      return f

        # If no priority match or not searching for priority fonts, use the first found
        font_path = all_found_fonts[0]
        print(f"✅ Found {name_for_log} font at: {font_path} (First match)")
        return font_path

    print(f"⚠️ WARNING: Could not find any {name_for_log} font for pattern '{glob_pattern}'")
    return None

def draw_text_with_fallback(draw, xy, text, fill, text_font, emoji_font_path, font_size):
    """Draws text char-by-char, trying emoji font if needed."""
    current_x = xy[0]
    y_pos = xy[1]
    emoji_font_instance = None # Lazy load emoji font

    # Attempt to load the emoji font instance ONCE if needed and possible
    # We try loading at the target size first, then fallback to 96 if that specific error occurs
    def get_emoji_font():
        nonlocal emoji_font_instance
        if emoji_font_instance or not emoji_font_path:
            return emoji_font_instance

        font_index = 0 # Assume first font in collection if .ttc/.otc
        try:
            emoji_font_instance = ImageFont.truetype(emoji_font_path, size=font_size, index=font_index)
        except (IOError, OSError) as e:
            if "invalid pixel size" in str(e).lower(): # Specific FreeType error
                try:
                    print(f"  ℹ️ Emoji font size {font_size} invalid, trying fallback size 96...")
                    emoji_font_instance = ImageFont.truetype(emoji_font_path, size=96, index=font_index)
                except (IOError, OSError) as e2:
                    print(f"  ❌ DEBUG: Failed to load emoji font at size {font_size} AND 96: {e2}")
                    emoji_font_instance = None # Fallback failed
            else:
                print(f"  ❌ DEBUG: Failed to load emoji font '{emoji_font_path}': {e}")
                emoji_font_instance = None # Other error
        except Exception as e: # Catch any other font loading errors
             print(f"  ❌ DEBUG: Unexpected error loading emoji font '{emoji_font_path}': {e}")
             emoji_font_instance = None
        return emoji_font_instance


    for char in text:
        font_to_use = text_font # Default to text font

        if is_emoji(char):
            loaded_emoji_font = get_emoji_font()
            if loaded_emoji_font:
                # Check if the specific emoji glyph exists in the loaded emoji font
                # Using getbbox might be more reliable than getmask across Pillow versions
                try:
                    bbox = loaded_emoji_font.getbbox(char)
                    # A valid bbox is usually (x0, y0, x1, y1) where x0 < x1 or y0 < y1
                    # A zero-width glyph might have x0==x1, check this condition
                    if bbox and (bbox[2] > bbox[0] or bbox[3] > bbox[1]):
                         font_to_use = loaded_emoji_font
                    # else: # Glyph not found or zero-width, keep using text_font (might render tofu)
                         # print(f"  ⚠️ Emoji '{char}' not found or zero-width in emoji font, using text font.")
                except Exception:
                     # print(f"  ⚠️ Error checking glyph for '{char}' in emoji font, using text font.")
                     pass # Keep using text_font on error
            # else: # Emoji font failed to load, keep using text_font

        # Draw the single character
        try:
            draw.text((current_x, y_pos), char, font=font_to_use, fill=fill)
        except Exception as e:
             print(f"  ❌ Error drawing character '{char}': {e}")
             continue # Skip drawing this char if it errors out

        # Increment X position using the font actually used
        try:
            # Use getlength if available (older Pillow)
             advance = font_to_use.getlength(char)
        except AttributeError:
             try:
                  # Use getbbox otherwise (newer Pillow)
                  bbox = font_to_use.getbbox(char)
                  # Advance is the width from the bounding box
                  advance = bbox[2] - bbox[0] if bbox else 0
             except Exception:
                  advance = font_size * 0.6 # Estimate if getbbox also fails
        except Exception:
             advance = font_size * 0.6 # General fallback estimate

        current_x += advance

def create_scrolling_gif(
    text,
    output_filename="post.gif",
    width=1200,
    height=628,
    bg_color="#e7973c", # Orange
    text_color="#FFFFFF" # White
):
    """Generates an animated GIF with scrolling text."""

    print(f"🎨 Starting GIF generation for text: \"{text}\"")
    # --- 1. Setup Fonts ---
    font_size = int(height * 0.15) # Aim for ~94px on 628 height
    print(f"  Target font size: {font_size}px")

    # Find font PATHS first
    text_font_path = find_font('*Noto*Sans*Regular*.ttf', "Text")
    emoji_font_path = find_font('Apple Color Emoji.ttc', "Apple Emoji") # Prioritize Apple
    if not emoji_font_path:
        emoji_font_path = find_font('*Noto*Color*Emoji*.ttf', "Noto Emoji") # Fallback to Noto

    text_font = None # Will hold the loaded ImageFont object

    # Load the primary text font
    try:
        if text_font_path:
            text_font = ImageFont.truetype(text_font_path, size=font_size)
            print(f"  Text font loaded: {text_font_path}")
        else:
            print("  ⚠️ Text font path not found. Falling back to Pillow default.")
            text_font = ImageFont.load_default()
            # Default font is small, adjust size estimate - This might not work well
            font_size = 20 # Arbitrary small size for default
    except (IOError, OSError) as e:
        print(f"  ❌ CRITICAL Error loading text font '{text_font_path}': {e}. Falling back to default.")
        text_font = ImageFont.load_default()
        font_size = 20
    except Exception as e:
         print(f"  ❌ CRITICAL Unexpected error loading text font '{text_font_path}': {e}. Falling back to default.")
         text_font = ImageFont.load_default()
         font_size = 20


    if not emoji_font_path:
        print("  ⚠️ No emoji font path found. Emojis may render as '□' (tofu) using the text font.")
        # Emoji font instance will remain None in draw_text_with_fallback

    # --- 2. Calculate Text Dimensions ---
    print("  Calculating text dimensions...")
    total_text_width = 0
    max_char_height = 0
    temp_emoji_font = None # To cache loaded emoji font for measurements

    # Helper to get emoji font for measurement, similar to drawing logic
    def get_emoji_font_for_measure():
        nonlocal temp_emoji_font
        if temp_emoji_font or not emoji_font_path: return temp_emoji_font
        font_index = 0
        try:
            temp_emoji_font = ImageFont.truetype(emoji_font_path, size=font_size, index=font_index)
        except (IOError, OSError) as e:
            if "invalid pixel size" in str(e).lower():
                try: temp_emoji_font = ImageFont.truetype(emoji_font_path, size=96, index=font_index)
                except Exception: temp_emoji_font = None
            else: temp_emoji_font = None
        except Exception: temp_emoji_font = None
        return temp_emoji_font

    for char in text:
        font_used_for_measure = text_font # Assume text font
        char_width = 0
        char_height = 0

        if is_emoji(char):
            loaded_emoji_font = get_emoji_font_for_measure()
            if loaded_emoji_font:
                 # Check if glyph exists before assuming emoji font for measurement
                try:
                    bbox = loaded_emoji_font.getbbox(char)
                    if bbox and (bbox[2] > bbox[0] or bbox[3] > bbox[1]):
                         font_used_for_measure = loaded_emoji_font
                except Exception:
                     pass # Stick with text_font if check fails

        # Get width and height using the determined font
        try:
            bbox = font_used_for_measure.getbbox(char)
            if bbox:
                 char_width = bbox[2] - bbox[0]
                 char_height = bbox[3] - bbox[1]
            else: # Fallback for space or chars with no bbox
                 char_width = font_used_for_measure.getlength(char) if hasattr(font_used_for_measure, 'getlength') else font_size * 0.3
                 char_height = font_size # Estimate height
        except AttributeError: # Fallback for older Pillow getlength
            try:
                char_width = font_used_for_measure.getlength(char)
                char_height = font_size # Estimate height
            except Exception:
                char_width = font_size * 0.6 # Estimate width if all fails
                char_height = font_size
        except Exception as e:
             print(f"    DEBUG: Error getting bbox/length for char '{char}': {e}")
             char_width = font_size * 0.6 # Estimate width
             char_height = font_size     # Estimate height


        total_text_width += char_width
        max_char_height = max(max_char_height, char_height)

    # --- Use calculated dimensions ---
    text_height = max_char_height if max_char_height > 0 else font_size # Use calculated height or estimate
    y_pos = (height - text_height) // 2 # Center vertically based on calculated max height
    gap = width // 3 # Gap between text repetitions
    total_scroll_width = int(total_text_width) + gap
    print(f"  Calculated text width: {total_text_width:.2f}px, max height: {text_height}px")
    print(f"  Total scroll width (text + gap): {total_scroll_width}px")

    # --- 3. Animation Parameters ---
    scroll_speed = 10 # Pixels per frame
    frame_duration_ms = 40 # 40ms = 25 FPS

    if total_scroll_width <= 0:
        print("❌ Error: Calculated total scroll width is zero or negative. Cannot generate animation.")
        return None

    num_frames = total_scroll_width // scroll_speed
    if num_frames <= 0:
        print("❌ Error: Calculated number of frames is zero or less. Increase text length or decrease scroll speed.")
        return None
    frames = []
    print(f"  Animation: {num_frames} frames, {scroll_speed}px/frame, {frame_duration_ms}ms/frame")

    # --- 4. Generate Frames ---
    print(f"⏳ Generating {num_frames} frames...")
    for i in range(num_frames):
        img = Image.new('RGB', (width, height), color=bg_color)
        d = ImageDraw.Draw(img)

        current_x_pos = width - (i * scroll_speed) # Start off-screen right, scroll left

        # Draw the text instance that scrolls across the screen
        draw_text_with_fallback(d, (current_x_pos, y_pos), text, text_color, text_font, emoji_font_path, font_size)

        # Draw the *next* instance of the text following it, separated by the gap
        # Its starting position is current_x_pos + text_width + gap = current_x_pos + total_scroll_width
        draw_text_with_fallback(d, (current_x_pos + total_scroll_width, y_pos), text, text_color, text_font, emoji_font_path, font_size)

        # Draw the *previous* instance if needed (for seamless loop start)
        # Its starting position is current_x_pos - total_scroll_width
        draw_text_with_fallback(d, (current_x_pos - total_scroll_width, y_pos), text, text_color, text_font, emoji_font_path, font_size)


        frames.append(img)
        # Simple progress indicator
        if (i + 1) % (num_frames // 10 or 1) == 0:
            print(f"  ...frame {i+1}/{num_frames}")


    # --- 5. Save the GIF ---
    print(f"💾 Saving GIF as '{output_filename}'...")
    try:
        frames[0].save(
            output_filename,
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration_ms,
            loop=0, # 0 = loop forever
            optimize=True # Try to reduce file size
        )
        print(f"✅ GIF saved successfully!")
        return output_filename
    except Exception as e:
        print(f"❌ Error saving GIF: {e}")
        return None


# --- Main Execution ---

def main():
    """Main function to orchestrate the publishing workflow."""
    print("--- Unified Social Publishing Sync ---")
    recent_files = find_recent_markdown_files(SYNC_PATH_STR)

    if not recent_files:
        print("No recent markdown files found to sync.")
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

    # --- Load and verify file content ---
    try:
        post = frontmatter.load(file_to_post)
        subject = post.metadata.get('title')
        description = post.metadata.get('description', '') # Optional
        permalink = post.metadata.get('permalink')
        markdown_content = post.content

        if not subject or not permalink:
            print("❌ 'title' and/or 'permalink' missing in frontmatter. Cannot proceed.")
            return

        full_url = urljoin(SITE_BASE_URL.strip('/'), permalink.strip('/')) # More robust URL joining

        print(f"\n📄 Selected file: {file_to_post.name}")
        print(f"   Subject: {subject}")
        print(f"   Permalink: {permalink}")
        print(f"   Full URL: {full_url}")

        if not check_url_status(full_url):
            print("   Post URL is not live yet. Please deploy your site and try again.")
            return

    except Exception as e:
        print(f"❌ Error reading or parsing the markdown file {file_to_post}: {e}")
        return

    # --- Platform Selection ---
    print("\nWhich platforms do you want to post to?")
    print("  1. Buttondown (Draft)")
    print("  2. LinkedIn")
    print("  3. GoToSocial")
    print("  4. All of the above")
    platform_choice = input("Enter your choice(s) (e.g., '1,3' or '4'): ").strip().lower()

    if not platform_choice:
        print("No platforms selected. Exiting.")
        return

    # Determine which platforms to target based on input
    choices = set(c.strip() for c in platform_choice.split(','))
    do_buttondown = '1' in choices or '4' in choices
    do_linkedin = '2' in choices or '4' in choices
    do_gotosocial = '3' in choices or '4' in choices

    if not (do_buttondown or do_linkedin or do_gotosocial):
         print("Invalid platform selection. Exiting.")
         return

    # --- LinkedIn Specific: GIF Generation Prompt ---
    gif_filename = None # Holds the path to the generated GIF if created
    if do_linkedin:
        generate_gif_choice = input("Generate and attach scrolling title GIF for LinkedIn? (y/N): ").lower()
        if generate_gif_choice == 'y':
            gif_output_path = f"temp_linkedin_{Path(file_to_post).stem}.gif" # Unique temp name
            print(f"\n✨ Generating GIF...")
            # Pass the subject (title) from frontmatter to the GIF function
            created_gif_path = create_scrolling_gif(subject, gif_output_path)
            if created_gif_path:
                gif_filename = created_gif_path # Store path if successful
            else:
                print("  ❌ GIF generation failed. Proceeding without GIF for LinkedIn.")
        else:
            print("Skipping GIF generation for LinkedIn.")


    # --- Process for each selected platform ---

    # Buttondown
    if do_buttondown:
        body_for_buttondown = markdown_content # Use raw markdown content
        print("\n" + "="*50)
        print("                DRY RUN for Buttondown")
        print("="*50)
        print(f"Subject: {subject}")
        print(f"Body (first 200 chars): {body_for_buttondown[:200].strip()}...")
        print("="*50)
        publish_choice = input(f"Create this draft in Buttondown? (y/N): ").lower()
        if publish_choice == 'y':
            post_to_buttondown(subject, body_for_buttondown)
        else:
            print("\nPublishing to Buttondown cancelled.")

    # LinkedIn
    if do_linkedin:
        linkedin_post_content = format_for_linkedin(subject, description, markdown_content, full_url)
        print("\n" + "="*50)
        print("                DRY RUN for LinkedIn")
        print("="*50)
        print(linkedin_post_content)
        print("="*50)
        print(f"Media to attach: {gif_filename if gif_filename else 'None'}")
        print("="*50)

        publish_choice = input(f"Publish this to LinkedIn {'with GIF' if gif_filename else '(text-only)'}? (y/N): ").lower()
        if publish_choice == 'y':
            success = False
            if gif_filename:
                # Attempt to post with media
                success = post_to_linkedin_with_media(linkedin_post_content, gif_filename, subject)
                # Clean up the temp GIF file AFTER attempting post
                try:
                    os.remove(gif_filename)
                    print(f"  🧹 Cleaned up temporary GIF file: {gif_filename}")
                except OSError as e:
                    print(f"  ⚠️ Warning: Could not remove temp GIF file {gif_filename}: {e}")
            else:
                # Post text only
                success = post_to_linkedin(linkedin_post_content)

            if not success:
                 print("  ❌ LinkedIn post failed.")
                 # Decide if you want to stop or continue with other platforms
                 # return # Example: stop if LinkedIn fails

        else:
            print("\nPublishing to LinkedIn cancelled.")
            # If cancelled, and GIF was generated, clean it up
            if gif_filename:
                 try:
                      os.remove(gif_filename)
                      print(f"  🧹 Cleaned up unused temporary GIF file: {gif_filename}")
                 except OSError as e:
                      print(f"  ⚠️ Warning: Could not remove unused temp GIF file {gif_filename}: {e}")

    # GoToSocial
    if do_gotosocial:
        gotosocial_post_content = format_for_gotosocial(subject, markdown_content, full_url)
        print("\n" + "="*50)
        print("                DRY RUN for GoToSocial")
        print("="*50)
        print(gotosocial_post_content)
        print("="*50)
        publish_choice = input(f"Publish this to GoToSocial? (y/N): ").lower()
        if publish_choice == 'y':
            post_to_gotosocial(gotosocial_post_content)
        else:
            print("\nPublishing to GoToSocial cancelled.")

    print("\n--- Sync Complete ---")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n\n❌ An unexpected error occurred: {e}")
        # Consider adding more detailed error logging here if needed