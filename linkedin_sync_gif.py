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


# --- NEW ---
def find_system_font(font_names):
    """Tries to find a usable .ttf font file from a list of common names/paths."""
    common_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", # Linux
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", # Linux
        "/System/Library/Fonts/Supplemental/Arial.ttf", # macOS
        "C:\\Windows\\Fonts\\arial.ttf", # Windows
        "arial.ttf" # Check current directory
    ]
    
    for name in font_names + common_paths:
        try:
            # Test loading the font
            ImageFont.truetype(name, size=10)
            return name
        except (IOError, OSError):
            continue
    
    print("⚠️  No system fonts found. Falling back to default built-in font (may be small).")
    return None # Will cause Pillow to use its default


# --- NEW ---
def create_scrolling_gif(
    text,
    output_filename="post.gif",
    width=1200,
    height=628,
    bg_color="#3498db", # A nice blue
    text_color="#FFFFFF" # White
):
    """
    Generates an animated GIF with scrolling text.
    """
    
    # --- 1. Setup Font ---
    # Make font size relative to image height
    font_size = int(height * 0.15)
    
    # Try to find a good system font
    font_path = find_system_font(["Arial", "Helvetica", "DejaVuSans"])
    
    try:
        if font_path:
            font = ImageFont.truetype(font_path, size=font_size)
        else:
            # Fallback to default bitmap font if no .ttf is found
            font = ImageFont.load_default()
            # Adjust size for default font
            font_size = 20
    except Exception as e:
        print(f"Error loading font: {e}. Falling back to default.")
        font = ImageFont.load_default()
        font_size = 20

    # --- 2. Calculate Dimensions ---
    # Use textbbox for more accurate size calculation
    try:
        # Get bounding box [left, top, right, bottom]
        bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError: # Fallback for older Pillow versions
        text_width, text_height = ImageDraw.Draw(Image.new("RGB", (1, 1))).textsize(text, font=font)
        
    y_pos = (height - text_height) // 2
    
    # We create a "loop" by having the text follow itself
    # Gap is 1/3 of the image width
    gap = width // 3
    total_scroll_width = text_width + gap
    
    # --- 3. Animation Parameters ---
    scroll_speed = 10 # Pixels per frame
    frame_duration_ms = 40 # 40ms = 25 FPS
    
    # Number of frames for one full loop
    num_frames = total_scroll_width // scroll_speed
    
    frames = []

    # --- 4. Generate Frames ---
    print(f"Generating {num_frames} frames for animation...")
    for i in range(num_frames):
        # Create a new blank frame
        img = Image.new('RGB', (width, height), color=bg_color)
        d = ImageDraw.Draw(img)
        
        # Calculate the X position for this frame
        current_x_pos = -(i * scroll_speed)
        
        # Draw the main text
        d.text((current_x_pos, y_pos), text, font=font, fill=text_color)
        
        # Draw the "next" text that follows it, creating the loop
        d.text((current_x_pos + total_scroll_width, y_pos), text, font=font, fill=text_color)
        
        frames.append(img)
    
    # --- 5. Save the GIF ---
    try:
        frames[0].save(
            output_filename,
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration_ms,
            loop=0, # 0 = loop forever
            optimize=True # Try to reduce file size
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
