import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configurations ---
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")

def debug_linkedin_token():
    """
    Inspects the current LinkedIn access token to verify its status and permissions (scopes).
    """
    if not all([LINKEDIN_ACCESS_TOKEN, LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET]):
        print("❌ Error: Make sure LINKEDIN_ACCESS_TOKEN, LINKEDIN_CLIENT_ID, and LINKEDIN_CLIENT_SECRET are in your .env file.")
        return

    url = "https://www.linkedin.com/oauth/v2/introspectToken"
    
    payload = {
        'token': LINKEDIN_ACCESS_TOKEN,
        'client_id': LINKEDIN_CLIENT_ID,
        'client_secret': LINKEDIN_CLIENT_SECRET
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    print("🔎 Inspecting your LinkedIn Access Token...")
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        
        token_info = response.json()
        
        print("\n--- Token Analysis ---")
        
        # Check if the token is active
        if token_info.get('active', False):
            print("✅ Status: Token is ACTIVE")
        else:
            print("❌ Status: Token is INACTIVE or expired. You must generate a new one.")
            return

        # Check the scopes (permissions)
        scopes = token_info.get('scope', '').split(' ')
        print("\nGranted Permissions (Scopes):")
        for scope in scopes:
            print(f"- {scope}")

        # Check specifically for the required scope
        if 'w_member_social' in scopes:
            print("\n✅ VERIFIED: The token has the required 'w_member_social' permission to post.")
        else:
            print("\n❌ CRITICAL ERROR: The token is MISSING the 'w_member_social' permission.")
            print("   This is the reason your posts are failing. You must re-run the `get_linkedin_token.py` script, ensuring you approve all permissions on the consent screen.")

        print("\n--- End of Analysis ---")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ An error occurred while contacting the LinkedIn API: {e}")
        if e.response is not None:
            print(f"   Response: {e.response.text}")

if __name__ == "__main__":
    debug_linkedin_token()