from pathlib import Path # --- NEW ---
import glob
import requests
import json
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone
import re
from markdownify import markdownify as md
from mimetypes import guess_type # --- NEW ---
import sys # --- NEW ---

# --- NEW: Import Pillow components ---
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: The 'Pillow' library is required. Please install it using: pip install Pillow")
    sys.exit(1)


# Load environment variables from .env file
load_dotenv()

# --- API Configurations ---
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_USER_ID = os.getenv("LINKEDIN_USER_ID")
LINKEDIN_AUTHOR = os.getenv("LINKEDIN_AUTHOR")  # e.g., "urn:li:person:xxxxxxxx"

# --- Verification ---
if not all([BUTTONDOWN_API_KEY, LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR]):
    raise ValueError("One or more required environment variables are missing in your .env file.")

# --- (Your existing get_weekly_emails_and_prompt function) ---
def get_weekly_emails_and_prompt():
    """
    Fetches all public emails from the last 7 days and prompts the user to select one.
    """
    headers = {"Authorization": f"Token {BUTTONDOWN_API_KEY}"}
    
    today = datetime.now(timezone.utc)
    start_date = today - timedelta(days=7)
    start_date_str = start_date.strftime('%Y-%m-%d')
    
    url = f"https://api.buttondown.email/v1/emails?ordering=-publish_date&type=public&publish_date__start={start_date_str}"

    try:
        print(f"▶️ Fetching emails since {start_date_str} from Buttondown...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        emails = response.json().get("results", [])

        if not emails:
            print("⏹️ No emails found in the last 7 days.")
            return None

        print("\n--- Emails Found in the Last 7 Days ---")
        for i, email in enumerate(emails):
            publish_date = datetime.fromisoformat(email['publish_date'].replace('Z', '+00:00'))
            date_display = publish_date.strftime('%Y-%m-%d (%a)')
            print(f"  {i + 1}. {date_display} - {email['subject']}")
        print("-" * 30)

        choice = input("Enter the number of the email to post (or press Enter to cancel): ")

        if not choice.strip():
            return None

        index = int(choice) - 1
        if 0 <= index < len(emails):
            selected_email = emails[index]
            print(f"✅ Selected: '{selected_email['subject']}'")
            return selected_email
        else:
            print("❌ Invalid number.")
            return None

    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"❌ An error occurred: {e}")
        return None

# --- (Your existing format_for_linkedin function) ---
def format_for_linkedin(subject, description, html_body, url):
    """
    Converts email HTML to a LinkedIn-friendly plain text format with footnote-style links.
    """

    footnotes = []
    def link_to_footnote(match):
        link_text = match.group(1)
        link_url = match.group(2)
        footnotes.append(link_url)
        return f"{link_text} [{len(footnotes)}]"

    def convert_md_table_to_list(match):
        table_text = match.group(0)
        lines = table_text.strip().split('\n')
        if len(lines) < 3: return table_text

        list_items = []
        for row in lines[2:]:
            columns = [col.strip() for col in row.split('|') if col.strip()]
            if len(columns) >= 3:
                symbol_match = re.search(r'\[(.*?)\]', columns[0])
                symbol = symbol_match.group(1) if symbol_match else columns[0]
                company = columns[1]
                change = columns[2]
                list_items.append(f"• {symbol} ({company}): {change}")
        return "\n".join(list_items)

    text = md(html_body, heading_style="ATX")

    text = text.replace('\\*', '*')
    text = text.replace('\\$', '$')
    text = text.replace('\\_', '_')
    
    text = re.sub(r'\{\{.*?\}\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(https?://[^\s]+)\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*---\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    table_pattern = re.compile(r'^\s*\|.*\|.*\n\s*\|[-|: ]+\|.*\n((?:\s*\|.*\|.*\n?)+)', re.MULTILINE)
    text = table_pattern.sub(convert_md_table_to_list, text)
    
    text = re.sub(r'\*\s*\[.*?\]\(.*?\)\s*\((.*?)\):\s*\*\*(.*?)\*\*', r'• \1: \2', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', link_to_footnote, text)
    
    text = re.sub(r'#+\s*📈\s*Markets Monday.*', '📈 Markets Monday', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🔥\s*Hot Takes Tuesday.*', '🔥 Hot Takes Tuesday', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🤪\s*Wacky Wednesday.*', '🤪 Wacky Wednesday', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🔙\s*Throwback Thursday.*', '🔙 Throwback Thursday', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*✅\s*Final Thoughts Friday.*', '✅ Final Thoughts Friday', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*🔮\s*Sneak Peak Saturday.*', '🔮 Sneak Peak Saturday', text, flags=re.IGNORECASE)
    
    text = re.sub(r'^#+\s*(.+)$', r'\n\n\1\n', text, flags=re.MULTILINE)
    
    text = re.sub(r'([\.!\?])\s*([A-Z])', r'\1\n\n\2', text)

    text = re.sub(r'(\*\*|__)', '', text)
    text = re.sub(r'^\s*[\*\-]\s*', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    footnote_section = ""
    if footnotes:
        footnote_lines = [f"[{i+1}] {url}" for i, url in enumerate(footnotes)]
        footnote_section = "\n\n" + "\n".join(footnote_lines)

    full_post = f"{subject}\n\n{description}\n\n{text}{footnote_section}\n\nRead the full post here: {url}"
    return full_post


# --- (Your existing post_to_linkedin function for TEXT-ONLY posts) ---
def post_to_linkedin(post_content):
    """Posts TEXT-ONLY content to LinkedIn."""
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
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    try:
        response = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=post_data)
        response.raise_for_status()
        print("\n✅ Successfully posted to LinkedIn!")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error posting to LinkedIn: {e}\n   Response: {e.response.text}")

def is_emoji(char):
    """
    Checks if a character is in a common emoji Unicode range.
    This is more reliable than font.getmask().
    """
    # U+1F300 to U+1F5FF (Misc Symbols and Pictographs, includes 🔮 1F52E, 📈 1F4C8, 🔥 1F525, 🔙 1F519)
    if '\U0001F300' <= char <= '\U0001F5FF':
        return True
    # U+1F600 to U+1F64F (Emoticons)
    if '\U0001F600' <= char <= '\U0001F64F':
        return True
    # U+1F900 to U+1F9FF (Supplemental Symbols, includes 🤪 1F92A)
    if '\U0001F900' <= char <= '\U0001F9FF':
        return True
    # U+2600 to U+27BF (Misc Symbols, includes ✅ 2705)
    if '\u2600' <= char <= '\u27BF':
        return True
    return False

# --- REVISED FUNCTION ---
def find_font(glob_pattern, name_for_log=""):
    """
    Finds a single font file matching a glob pattern across common system dirs.
    """
    if not name_for_log:
        name_for_log = glob_pattern

    # --- FIX #1: Use the CORRECT hardcoded path with spaces ---
    if glob_pattern == 'Apple Color Emoji.ttc':
        apple_path = '/System/Library/Fonts/Apple Color Emoji.ttc'
        if Path(apple_path).is_file():
            print(f"✅ Found {name_for_log} font at: {apple_path} (Hardcoded path)")
            return apple_path
        # If it's not there, we'll fall through to the glob search below.

    font_dirs_to_search = [
        os.path.expanduser('~/Library/Fonts/'), # Mac User
        '/Library/Fonts/',                        # Mac System
        '/System/Library/Fonts/',                 # Mac System
        '/System/Library/Fonts/Core/',            # Mac System (alternate)
        '/usr/share/fonts/truetype/noto/',        # Linux (Ubuntu)
        '/usr/share/fonts/noto/',                 # Linux (Arch)
        'C:\\Windows\\Fonts\\'                    # Windows
    ]
    
    all_found_fonts = []
    for font_dir in font_dirs_to_search:
        # Use recursive glob (**) to find files in subdirectories
        search_path = os.path.join(font_dir, '**', glob_pattern)
        try:
            # Set recursive=True to search subfolders
            found_fonts = glob.glob(search_path, recursive=True)
            if found_fonts:
                all_found_fonts.extend(found_fonts)
        except Exception as e:
            # Fallback for older python versions
            try:
                search_path_non_recursive = os.path.join(font_dir, glob_pattern)
                found_fonts_non_recursive = glob.glob(search_path_non_recursive)
                if found_fonts_non_recursive:
                    all_found_fonts.extend(found_fonts_non_recursive)
            except Exception:
                pass # Ignore errors from this path

    if all_found_fonts:
        all_found_fonts.sort()
        
        # --- FIX #2: Prioritize the *main* Noto Sans font over variants ---
        if 'Noto*Sans*Regular' in glob_pattern:
            for f in all_found_fonts:
                # Look for the plainest, most default version
                if f.endswith('NotoSans-Regular.ttf'):
                    print(f"✅ Found {name_for_log} font at: {f} (Prioritized)")
                    return f

        # If no priority match, just use the first one
        font_path = all_found_fonts[0]
        print(f"✅ Found {name_for_log} font at: {font_path}")
        return font_path
    
    print(f"⚠️  WARNING: Could not find any {name_for_log} font for pattern '{glob_pattern}'")
    return None

# --- REVISED FUNCTION ---
def draw_text_with_fallback(draw, xy, text, fill, text_font, emoji_font_path, font_size):
    """
    Draws text char-by-char, trying two different sizes for the emoji font
    if a glyph is missing from the main text_font.
    """
    current_x = xy[0]
    y_pos = xy[1]
    emoji_font_instance = None # We will load this if we need it

    for char in text:
        font_to_use = text_font
        
        if is_emoji(char) and emoji_font_path:
            # This is an emoji, so we *must* try to use the emoji font
            if not emoji_font_instance:
                font_index = 0 if emoji_font_path.endswith(".ttc") else 0
                try:
                    # --- THIS IS THE FIX (Step 1) ---
                    # First, try to load at the *exact* calculated size
                    emoji_font_instance = ImageFont.truetype(emoji_font_path, size=font_size, index=font_index)
                except (IOError, OSError) as e:
                    # --- THIS IS THE FIX (Step 2) ---
                    # If that fails, try the 'known-good' 96
                    if "invalid pixel size" in str(e):
                        try:
                            emoji_font_instance = ImageFont.truetype(emoji_font_path, size=96, index=font_index)
                        except (IOError, OSError) as e2:
                            print(f"--- DEBUG: Failed to load emoji font at size {font_size} AND 96: {e2} ---")
                            emoji_font_instance = text_font # Give up
                    else:
                        # A different error (e.g., file not found)
                        print(f"--- DEBUG: Failed to load emoji font: {e} ---")
                        emoji_font_instance = text_font # Give up
            
            font_to_use = emoji_font_instance
        
        # Draw the single character
        draw.text((current_x, y_pos), char, font=font_to_use, fill=fill)
        
        # Increment X position
        try:
            current_x += font_to_use.getlength(char)
        except AttributeError:
            bbox = font_to_use.getbbox(char)
            current_x += bbox[2] - bbox[0]

# --- REVISED FUNCTION ---
def create_scrolling_gif(
    text,
    output_filename="post.gif",
    width=1200,
    height=628,
    bg_color="#e7973c", # A nice orange
    text_color="#FFFFFF" # White
):
    """
    Generates an animated GIF with scrolling text, using separate fonts
    for text and emoji.
    """
    
    # --- 1. Setup Fonts (REVISED) ---
    font_size = int(height * 0.15) # This will be ~94
    
    # Find the font PATHS
    text_font_path = find_font('*Noto*Sans*Regular*.ttf', "Text")
    
    # Prioritize Apple's native font
    emoji_font_path = find_font('Apple Color Emoji.ttc', "Apple Emoji")
    
    # Fallback for Linux/other systems if Apple Emoji isn't found
    if not emoji_font_path:
        emoji_font_path = find_font('*Noto*Color*Emoji*.ttf', "Emoji")
    
    text_font = None
    
    # We ONLY load the text_font here.
    try:
        if text_font_path:
            text_font = ImageFont.truetype(text_font_path, size=font_size)
        else:
            print("Falling back to default font for TEXT")
            text_font = ImageFont.load_default()
            font_size = 20 # Adjust size for default
    except (IOError, OSError) as e:
        print(f"CRITICAL Error loading text font: {e}. Falling back to default.")
        text_font = ImageFont.load_default()
        font_size = 20
        
    if not emoji_font_path:
        print("No emoji font path found, will render '□' for emoji.")
        emoji_font_path = text_font_path

    # --- 2. Calculate Dimensions ---
    total_text_width = 0
    text_height = 0
    temp_emoji_font = None # To cache the loaded font
    
    for char in text:
        try:
            # Use is_emoji() to decide which font to use for calculation
            if not is_emoji(char):
                # This is a regular text character
                total_text_width += text_font.getlength(char)
                bbox = text_font.getbbox(char)
                text_height = max(text_height, bbox[3] - bbox[1])
            
            # This is an emoji character
            elif emoji_font_path:
                if not temp_emoji_font: # Load it once
                    font_index = 0 if emoji_font_path.endswith(".ttc") else 0
                    try:
                        # --- THIS IS THE FIX (Step 1) ---
                        temp_emoji_font = ImageFont.truetype(emoji_font_path, size=font_size, index=font_index)
                    except (IOError, OSError) as e:
                        # --- THIS IS THE FIX (Step 2) ---
                        if "invalid pixel size" in str(e):
                            try:
                                temp_emoji_font = ImageFont.truetype(emoji_font_path, size=96, index=font_index)
                            except (IOError, OSError) as e2:
                                print(f"--- DEBUG (Calc): Failed to load emoji font at size {font_size} AND 96: {e2} ---")
                                temp_emoji_font = text_font # Give up
                        else:
                            print(f"--- DEBUG (Calc): Failed to load emoji font: {e} ---")
                            temp_emoji_font = text_font # Give up

                total_text_width += temp_emoji_font.getlength(char)
                bbox = temp_emoji_font.getbbox(char)
                text_height = max(text_height, bbox[3] - bbox[1])
            else:
                # Tofu (no emoji font path)
                total_text_width += text_font.getlength(char)
        
        except Exception as e:
             # Fallback for errors on this char
             print(f"--- DEBUG: Error calculating width for char '{char}': {e} ---")
             total_text_width += text_font.getlength(char)

    y_pos = (height - text_height) // 2
    gap = width // 3
    total_scroll_width = int(total_text_width) + gap
    
    # --- 3. Animation Parameters ---
    # --- TYPO FIX ---
    scroll_speed = 10 # Pixels per frame
    frame_duration_ms = 40 # 40ms = 25 FPS
    
    if total_scroll_width <= 0:
        print("Error: Calculated text width is zero. Cannot generate animation.")
        return None
        
    num_frames = total_scroll_width // scroll_speed
    frames = []

    # --- 4. Generate Frames ---
    print(f"Generating {num_frames} frames for animation...")
    for i in range(num_frames):
        img = Image.new('RGB', (width, height), color=bg_color)
        d = ImageDraw.Draw(img)
        
        current_x_pos = -(i * scroll_speed)
        
        # Pass font_size to the helper
        draw_text_with_fallback(d, (current_x_pos, y_pos), text, text_color, text_font, emoji_font_path, font_size)
        
        # Draw the "next" text that follows it
        draw_text_with_fallback(d, (current_x_pos + total_scroll_width, y_pos), text, text_color, text_font, emoji_font_path, font_size)
        
        frames.append(img)
    
    # --- 5. Save the GIF ---
    try:
        frames[0].save(
            output_filename,
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration_ms,
            loop=0, # 0 = loop forever
            optimize=True
        )
        print(f"✅ GIF saved as '{output_filename}'")
        return output_filename
    except Exception as e:
        print(f"❌ Error saving GIF: {e}")
        return None

# --- NEW ---
def post_to_linkedin_with_media(post_content, media_filename, subject):
    """
    Posts content with an image/GIF to LinkedIn.
    This is a multi-step process:
    1. Register the upload
    2. Upload the media file
    3. Create the post with the uploaded media
    """
    print("Starting LinkedIn post with media...")
    
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
        print(f"\n❌ Error registering upload: {e}\n   Response: {e.response.text}")
        return

    # === 2. Upload the Media File ===
    print(f"  2. Uploading '{media_filename}'...")
    
    content_type, _ = guess_type(media_filename)
    if not content_type:
        content_type = "image/gif" # Default
        
    upload_headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": content_type
    }
    
    try:
        with open(media_filename, 'rb') as f:
            media_data = f.read()
            
        r_upload = requests.put(
            upload_url,
            headers=upload_headers,
            data=media_data
        )
        r_upload.raise_for_status()
        print("  ✅ Media file uploaded successfully.")
        
    except (requests.exceptions.RequestException, IOError) as e:
        print(f"\n❌ Error uploading media: {e}")
        if hasattr(e, 'response'):
             print(f"   Response: {e.response.text}")
        return

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
                "shareMediaCategory": "IMAGE", # Use "IMAGE" for GIFs
                "media": [{
                    "status": "READY",
                    "description": {"text": "Animated post title"},
                    "media": asset_urn,
                    "title": {"text": subject}
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
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error creating final post: {e}\n   Response: {e.response.text}")


# --- MODIFIED ---
def main():
    try:
        email_to_post = get_weekly_emails_and_prompt()

        if not email_to_post:
            print("No email selected. Exiting script.")
            return

        subject = email_to_post.get('subject', 'No Subject')
        description = email_to_post.get('description', '')
        body = email_to_post.get('body', 'No Body Content')
        email_url = email_to_post.get('absolute_url', '#')

        linkedin_post = format_for_linkedin(subject, description, body, email_url)

        print("\n" + "="*50)
        print("                DRY RUN")
        print("This will be posted to LinkedIn:")
        print("="*50 + "\n")
        print(linkedin_post)
        print("\n" + "="*50)

        # --- NEW: Ask to generate GIF ---
        gif_filename = None
        generate_gif_choice = input("Generate and attach scrolling title GIF? (y/N): ")
        if generate_gif_choice.lower() == 'y':
            gif_filename = "temp_linkedin_post.gif"
            create_scrolling_gif(subject, gif_filename)
        else:
            print("Skipping GIF generation.")
        
        # --- MODIFIED: Choose which post function to use ---
        publish_choice = input("Do you want to publish this to LinkedIn? (y/N): ")
        if publish_choice.lower() == 'y':
            
            if gif_filename:
                print("\nPublishing to LinkedIn with GIF...")
                post_to_linkedin_with_media(linkedin_post, gif_filename, subject)
                # Clean up the temp file
                try:
                    os.remove(gif_filename)
                    print(f"Cleaned up {gif_filename}")
                except OSError as e:
                    print(f"Warning: Could not remove temp file {gif_filename}: {e}")
            else:
                print("\nPublishing to LinkedIn (text-only)...")
                post_to_linkedin(linkedin_post)
        else:
            print("\nPublishing cancelled.")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")

if __name__ == "__main__":
    main()
