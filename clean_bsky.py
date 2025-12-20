import datetime
import os
from dotenv import load_dotenv
from atproto import Client, exceptions

# Load variables from .env file
load_dotenv()

# --- CONFIGURATION ---
HANDLE = os.getenv("BLUESKY_HANDLE")
APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD")
DRY_RUN = False  # Set to False to actually delete posts!
# ---------------------

def delete_todays_posts():
    # Validation: Ensure credentials exist
    if not HANDLE or not APP_PASSWORD:
        print("Error: Credentials missing. Please check your .env file.")
        return

    client = Client()
    
    try:
        print(f"Logging in as {HANDLE}...")
        client.login(HANDLE, APP_PASSWORD)
        
        # Bluesky timestamps are in UTC
        today = datetime.datetime.now(datetime.timezone.utc).date()
        print(f"Searching for posts made on: {today}")

        # Fetch the latest 50 posts from your feed
        response = client.get_author_feed(actor=HANDLE, limit=50)
        
        deleted_count = 0
        
        for feed_view in response.feed:
            post = feed_view.post
            post_date = datetime.datetime.fromisoformat(post.record.created_at).date()
            
            if post_date == today:
                print(f"\n[MATCH] Found post from {post.record.created_at}:")
                print(f"Content: {post.record.text[:50]}...")
                
                if DRY_RUN:
                    print(">>> DRY RUN: Post would be deleted.")
                else:
                    try:
                        client.delete_post(post.uri)
                        print(">>> SUCCESS: Post deleted.")
                    except Exception as e:
                        print(f">>> ERROR: Could not delete post: {e}")
                
                deleted_count += 1

        print(f"\nTask complete. Total posts identified: {deleted_count}")
        if DRY_RUN and deleted_count > 0:
            print("To actually delete these, set 'DRY_RUN = False' in the script.")

    except exceptions.AtProtocolError as e:
        print(f"Authentication failed: {e}")

if __name__ == "__main__":
    delete_todays_posts()
