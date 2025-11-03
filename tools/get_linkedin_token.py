import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000"

def get_authorization_code():
    # This URL now ONLY requests the one scope you need and are approved for.
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&scope=w_member_social"
    )
    print("Go to this URL in your browser and authorize the app:")
    print(auth_url)
    authorization_code = input("Enter the authorization code from the URL: ")
    return authorization_code

def get_access_token(authorization_code):
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    payload = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(token_url, data=payload)
    if response.status_code == 200:
        access_token = response.json()["access_token"]
        print("\n✅ Your NEW Access Token is:")
        print(access_token)
        print("\nUpdate your .env file with this new token.")
    else:
        print(f"\n❌ Error getting access token: {response.text}")

if __name__ == "__main__":
    if not all([CLIENT_ID, CLIENT_SECRET]):
        print("❌ Error: LINKEDIN_CLIENT_ID or LINKEDIN_CLIENT_SECRET not found in .env file.")
    else:
        code = get_authorization_code()
        if code:
            get_access_token(code)