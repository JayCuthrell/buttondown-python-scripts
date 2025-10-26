import requests
import json
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone
import google.generativeai as genai
from pathlib import Path
import glob
from mimetypes import guess_type
import sys

# --- Import Pillow components ---
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: The 'Pillow' library is required. Please install it using: pip install Pillow")
    sys.exit(1)


# === Load Environment Variables ===
load_dotenv()

# === API Configurations ===
BUTTONDOWN_API_KEY = os.getenv("BUTTONDOWN_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_AUTHOR = os.getenv("LINKEDIN_AUTHOR")  # e.g., "urn:li:person:xxxxxxxx"

# --- Verification ---
if not all([BUTTONDOWN_API_KEY, GOOGLE_API_KEY, LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR]):
    raise ValueError("One or more required environment variables are missing in your .env file. (Requires: BUTTONDOWN_API_KEY, GOOGLE_API_KEY, LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR)")

# --- Google Gemini API Configuration ---
genai.configure(api_key=GOOGLE_API_KEY)
# Using 1.5 Pro as a robust and widely available model
model = genai.GenerativeModel('gemini-2.5-pro') 

# --- Buttondown API Configuration ---
BUTTONDOWN_BASE_URL = "https://api.buttondown.email"
BUTTONDOWN_ENDPOINT = "/emails"


# === Function from linkedin_post_generator.py ===
def get_latest_sunday_buttondown_email():
    """
    Fetches the most recent public email from Buttondown that was published on a Sunday.
    This version filters by a date range to ensure we capture the most recent Sunday.
    """
    headers = {
        "Authorization": f"Token {BUTTONDOWN_API_KEY}",
    }
    
    # Calculate the date 14 days ago to ensure we capture at least two weeks of emails.
    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
    
    # Format the date into a simple YYYY-MM-DD format.
    formatted_date = two_weeks_ago.strftime('%Y-%m-%d')
    
    # Use the publish_date__start filter to get all emails published in the last 14 days.
    FILTERS = f"?ordering=-publish_date&type=public&publish_date__start={formatted_date}"

    try:
        print(f"▶️ Fetching recent public emails from Buttondown (since {formatted_date})...")
        response = requests.get(f"{BUTTONDOWN_BASE_URL}/v1{BUTTONDOWN_ENDPOINT}{FILTERS}", headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = json.loads(response.content)
        emails = data.get("results", [])

        if not emails:
            print("⏹️ No emails found from Buttondown API in the specified date range.")
            return None

        # Iterate through the fetched emails to find the most recent one published on a Sunday.
        for email in emails:
            publish_date_str = email.get('publish_date')
            if publish_date_str:
                # The 'Z' at the end of the timestamp indicates UTC. `fromisoformat` can handle this.
                publish_date = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
                
                # Check if the day of the week is Sunday.
                # Monday is 0 and Sunday is 6.
                if publish_date.weekday() == 6:
                    print(f"✅ Found latest Sunday email: '{email.get('subject')}' (Published: {publish_date.date()})")
                    return email

        print("⏹️ No Sunday email found in the recent batch of emails.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching email from Buttondown: {e}")
        return None
    except json.JSONDecodeError:
        print("❌ Error decoding JSON response from Buttondown.")
        return None

# === Function from linkedin_post_generator.py ===
def summarize_with_gemini(email_subject, email_body, email_url):
    """
    Uses Google Gemini to summarize the email content for LinkedIn,
    retaining writing style and adhering to LinkedIn repackaging strategy.
    """
    print("🤖 Asking Gemini to generate the LinkedIn post...")
    prompt = f"""
    You are an expert content repackager for LinkedIn. Your task is to summarize the following email content for a LinkedIn post.
    The summary needs to be engaging, value-driven, and adhere to the "Repackage and React Strategy" for LinkedIn.

    Here are the key guidelines for the LinkedIn post:
    - Always print the Email Subject exactly as the first line including the spicy emoji.
    - Include 2-4 insights or takeaways from the content that fits on the first few lines of a LinkedIn post to grab attention.
    - Include a takeaway for each day of the week from the headings related content and be sure to include the emoji per day without changing to be consistent and match the original content.
    - Make the value clear in the first two opening lines.
    - Open with your most interesting, eye-catching, or differentiated points.
    - Retain the original writing style of the email as much as possible.
    - Remember that the content is in reference to at least five (5) company names at a minimum.
    - Determine each and every company mentioned in each and every techmeme.com URL by extracting each and every one of the company names from the headlines of the articles referenced.
    - Include an exhaustive alphabetically ordered list of each and every one of company names referenced in the techmeme.com linked articles.
    - Include the link to the post {email_url} 
    - Do not use markdown style formatting such as asterisks or stars *

    ---
    Email Subject: {email_subject}
    ---
    Email Body:
    {email_body}

    Email URL: {email_url}
    ---

    Please provide a copy-paste ready LinkedIn post based on the above guidelines.
    """
    try:
        response = model.generate_content(prompt)
        print("✅ Gemini summary generated.")
        return response.text
    except Exception as e:
        print(f"❌ Error generating summary with Gemini: {e}")
        return "Could not generate summary."

# === Functions from linkedin_sync_gif.py (Text-Only Post) ===
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

# === Functions from linkedin_sync_gif.py (GIF Creation) ===

def is_emoji(char):
    """
    Checks if a character is in a common emoji Unicode range.
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

def find_font(glob_pattern, name_for_log=""):
    """
    Finds a single font file matching a glob pattern across common system dirs.
    """
    if not name_for_log:
        name_for_log = glob_pattern

    if glob_pattern == 'Apple Color Emoji.ttc':
        apple_path = '/System/Library/Fonts/Apple Color Emoji.ttc'
        if Path(apple_path).is_file():
            print(f"✅ Found {name_for_log} font at: {apple_path} (Hardcoded path)")
            return apple_path

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
        search_path = os.path.join(font_dir, '**', glob_pattern)
        try:
            found_fonts = glob.glob(search_path, recursive=True)
            if found_fonts:
                all_found_fonts.extend(found_fonts)
        except Exception as e:
            try:
                search_path_non_recursive = os.path.join(font_dir, glob_pattern)
                found_fonts_non_recursive = glob.glob(search_path_non_recursive)
                if found_fonts_non_recursive:
                    all_found_fonts.extend(found_fonts_non_recursive)
            except Exception:
                pass 

    if all_found_fonts:
        all_found_fonts.sort()
        
        if 'Noto*Sans*Regular' in glob_pattern:
            for f in all_found_fonts:
                if f.endswith('NotoSans-Regular.ttf'):
                    print(f"✅ Found {name_for_log} font at: {f} (Prioritized)")
                    return f

        font_path = all_found_fonts[0]
        print(f"✅ Found {name_for_log} font at: {font_path}")
        return font_path
    
    print(f"⚠️  WARNING: Could not find any {name_for_log} font for pattern '{glob_pattern}'")
    return None

def draw_text_with_fallback(draw, xy, text, fill, text_font, emoji_font_path, font_size):
    """
    Draws text char-by-char, trying two different sizes for the emoji font
    if a glyph is missing from the main text_font.
    """
    current_x = xy[0]
    y_pos = xy[1]
    emoji_font_instance = None 

    for char in text:
        font_to_use = text_font
        
        if is_emoji(char) and emoji_font_path:
            if not emoji_font_instance:
                font_index = 0 if emoji_font_path.endswith(".ttc") else 0
                try:
                    emoji_font_instance = ImageFont.truetype(emoji_font_path, size=font_size, index=font_index)
                except (IOError, OSError) as e:
                    if "invalid pixel size" in str(e):
                        try:
                            emoji_font_instance = ImageFont.truetype(emoji_font_path, size=96, index=font_index)
                        except (IOError, OSError) as e2:
                            print(f"--- DEBUG: Failed to load emoji font at size {font_size} AND 96: {e2} ---")
                            emoji_font_instance = text_font 
                    else:
                        print(f"--- DEBUG: Failed to load emoji font: {e} ---")
                        emoji_font_instance = text_font 
            
            font_to_use = emoji_font_instance
        
        draw.text((current_x, y_pos), char, font=font_to_use, fill=fill)
        
        try:
            current_x += font_to_use.getlength(char)
        except AttributeError:
            bbox = font_to_use.getbbox(char)
            current_x += bbox[2] - bbox[0]

def create_scrolling_gif(
    text,
    output_filename="post.gif",
    width=1200,
    height=628,
    bg_color="#e7973c", 
    text_color="#FFFFFF"
):
    """
    Generates an animated GIF with scrolling text, using separate fonts
    for text and emoji.
    """
    
    print(f"🎨 Starting GIF generation for text: \"{text}\"")
    # --- 1. Setup Fonts ---
    font_size = int(height * 0.15) # ~94
    
    text_font_path = find_font('*Noto*Sans*Regular*.ttf', "Text")
    emoji_font_path = find_font('Apple Color Emoji.ttc', "Apple Emoji")
    
    if not emoji_font_path:
        emoji_font_path = find_font('*Noto*Color*Emoji*.ttf', "Emoji")
    
    text_font = None
    
    try:
        if text_font_path:
            text_font = ImageFont.truetype(text_font_path, size=font_size)
        else:
            print("Falling back to default font for TEXT")
            text_font = ImageFont.load_default()
            font_size = 20
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
    temp_emoji_font = None 
    
    for char in text:
        try:
            if not is_emoji(char):
                total_text_width += text_font.getlength(char)
                bbox = text_font.getbbox(char)
                text_height = max(text_height, bbox[3] - bbox[1])
            
            elif emoji_font_path:
                if not temp_emoji_font: 
                    font_index = 0 if emoji_font_path.endswith(".ttc") else 0
                    try:
                        temp_emoji_font = ImageFont.truetype(emoji_font_path, size=font_size, index=font_index)
                    except (IOError, OSError) as e:
                        if "invalid pixel size" in str(e):
                            try:
                                temp_emoji_font = ImageFont.truetype(emoji_font_path, size=96, index=font_index)
                            except (IOError, OSError) as e2:
                                print(f"--- DEBUG (Calc): Failed to load emoji font at size {font_size} AND 96: {e2} ---")
                                temp_emoji_font = text_font 
                        else:
                            print(f"--- DEBUG (Calc): Failed to load emoji font: {e} ---")
                            temp_emoji_font = text_font 

                total_text_width += temp_emoji_font.getlength(char)
                bbox = temp_emoji_font.getbbox(char)
                text_height = max(text_height, bbox[3] - bbox[1])
            else:
                total_text_width += text_font.getlength(char)
        
        except Exception as e:
             print(f"--- DEBUG: Error calculating width for char '{char}': {e} ---")
             total_text_width += text_font.getlength(char)

    y_pos = (height - text_height) // 2
    gap = width // 3
    total_scroll_width = int(total_text_width) + gap
    
    # --- 3. Animation Parameters ---
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
        
        draw_text_with_fallback(d, (current_x_pos, y_pos), text, text_color, text_font, emoji_font_path, font_size)
        draw_text_with_fallback(d, (current_x_pos + total_scroll_width, y_pos), text, text_color, text_font, emoji_font_path, font_size)
        
        frames.append(img)
    
    # --- 5. Save the GIF ---
    try:
        frames[0].save(
            output_filename,
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration_ms,
            loop=0, 
            optimize=True
        )
        print(f"✅ GIF saved as '{output_filename}'")
        return output_filename
    except Exception as e:
        print(f"❌ Error saving GIF: {e}")
        return None

# === Functions from linkedin_sync_gif.py (Media Post) ===
def post_to_linkedin_with_media(post_content, media_filename, subject):
    """
    Posts content with an image/GIF to LinkedIn.
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
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"], 
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
        content_type = "image/gif" 
        
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


# === NEW Merged main() Function ===
def main():
    try:
        # 1. Fetch latest Sunday email (from linkedin_post_generator.py)
        email_to_post = get_latest_sunday_buttondown_email()

        if not email_to_post:
            print("No Sunday email found. Exiting script.")
            return

        subject = email_to_post.get('subject', 'No Subject')
        body = email_to_post.get('body', 'No Body Content')
        email_url = email_to_post.get('absolute_url', '#')

        # 2. Generate post content with Gemini (from linkedin_post_generator.py)
        linkedin_post = summarize_with_gemini(subject, body, email_url)

        # 3. Show "Dry Run" (from linkedin_sync_gif.py)
        print("\n" + "="*50)
        print("                DRY RUN")
        print("This will be posted to LinkedIn:")
        print("="*50 + "\n")
        print(linkedin_post)
        print("\n" + "="*50)

        # 4. Ask to generate GIF (from linkedin_sync_gif.py)
        gif_filename = None
        generate_gif_choice = input("Generate and attach scrolling title GIF? (y/N): ")
        if generate_gif_choice.lower() == 'y':
            gif_filename = "temp_linkedin_post.gif"
            # Use the 'subject' from the email for the GIF
            create_scrolling_gif(subject, gif_filename)
        else:
            print("Skipping GIF generation.")
        
        # 5. Ask to publish (from linkedin_sync_gif.py)
        publish_choice = input("Do you want to publish this to LinkedIn? (y/N): ")
        if publish_choice.lower() == 'y':
            
            if gif_filename:
                # Post WITH GIF
                print("\nPublishing to LinkedIn with GIF...")
                post_to_linkedin_with_media(linkedin_post, gif_filename, subject)
                
                # Clean up the temp file
                try:
                    os.remove(gif_filename)
                    print(f"Cleaned up {gif_filename}")
                except OSError as e:
                    print(f"Warning: Could not remove temp file {gif_filename}: {e}")
            else:
                # Post TEXT-ONLY
                print("\nPublishing to LinkedIn (text-only)...")
                post_to_linkedin(linkedin_post)
        else:
            print("\nPublishing cancelled.")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")

if __name__ == "__main__":
    main()