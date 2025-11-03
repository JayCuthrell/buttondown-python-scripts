import os
import frontmatter
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

# --- NEW: Import from your modules ---
from modules.buttondown_api import post_to_buttondown
from modules.linkedin_api import format_for_linkedin, post_to_linkedin, post_to_linkedin_with_media
from modules.gotosocial_api import format_for_gotosocial, post_to_gotosocial
from modules.image_utils import create_scrolling_gif
# We can also move find_recent_markdown_files and check_url_status to a file_utils.py module
from modules.file_utils import find_recent_markdown_files, check_url_status 

# --- Load Environment Variables ---
load_dotenv()
# Note: API keys are now loaded inside their respective modules,
# but we still need these paths for the main script logic.
SYNC_PATH_STR = os.getenv("SYNC_PATH")
SITE_BASE_URL = os.getenv("SITE_BASE_URL")

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