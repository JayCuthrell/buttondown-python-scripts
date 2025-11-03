import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")

def check_profile_access():
    """
    Uses the access token to make a simple GET request to the /me endpoint.
    """
    if not LINKEDIN_ACCESS_TOKEN:
        print("❌ LINKEDIN_ACCESS_TOKEN not found in .env file.")
        return

    print("🔎 Checking basic token access by fetching profile...")
    
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}"
    }
    url = "https://api.linkedin.com/v2/me"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        print("\n✅ SUCCESS: The token successfully fetched basic profile data.")
        print("This means the token is valid, but the 'w_member_social' permission is being blocked by LinkedIn.")
        print("\n--- Profile Data ---")
        print(response.json())
        print("--------------------")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ FAILED: The token could not fetch basic profile data.")
        print(f"   Error: {e}")
        if e.response is not None:
            print(f"   Response: {e.response.text}")

if __name__ == "__main__":
    check_profile_access()