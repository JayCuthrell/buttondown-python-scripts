# Import necessary libraries
# requests: For making HTTP requests to the LinkedIn API.
# dotenv: For loading and saving credentials to a .env file.
# os: To access environment variables.
# urllib.parse: To correctly format URLs.
import requests
from dotenv import load_dotenv, set_key
import os
import urllib.parse

# Load existing environment variables from the .env file into the script's environment.
load_dotenv()

# --- Step 1: Initial Setup and Authorization URL ---

# Retrieve your app's Client ID and Secret from the .env file.
client_id = os.getenv('LINKEDIN_CLIENT_ID')
client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')

# Define the Redirect URI. This script uses a special tool provided by LinkedIn
# for developers, which avoids the need to run a local web server.
# The URI is URL-encoded to ensure it's transmitted correctly.
redirect_uri = urllib.parse.quote('https://www.linkedin.com/developers/tools/oauth/redirect')
authorization_url = 'https://www.linkedin.com/oauth/v2/authorization'



# Define the permissions (scopes) the app is requesting.
# 'openid', 'profile', 'email' are for the "Sign In with LinkedIn" product.
# 'w_member_social' is for the "Share on LinkedIn" product.
# The scopes are separated by a URL-encoded space (%20).
scope = 'openid%20profile%20email%20w_member_social'

# Construct the full authorization URL that the user will visit in their browser.
full_auth_url = f"{authorization_url}?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}"
print("Go to this URL to authorize:", full_auth_url)

# --- Step 2: Exchange Authorization Code for Access Token ---

# Prompt the user to paste the authorization code they get after approving the app in their browser.
authorization_code = input("Enter the authorization code: ")

# Define the URL for exchanging the code for an access token.
token_url = 'https://www.linkedin.com/oauth/v2/accessToken'

# Prepare the payload for the POST request, including the authorization code.
payload = {
    'grant_type': 'authorization_code',
    'code': authorization_code,
    'redirect_uri': urllib.parse.unquote(redirect_uri), # The redirect_uri must match the one used in the initial request.
    'client_id': client_id,
    'client_secret': client_secret
}
# Make the POST request to get the token.
response = requests.post(token_url, data=payload)

# Check if the request was successful.
if response.status_code == 200:
    # Extract the access token from the JSON response.
    access_token = response.json().get('access_token')
    print("Access Token:", access_token)

    # Use the 'set_key' function to automatically save the access token to the .env file.
    # This avoids having to copy and paste it manually.
    set_key('.env', 'LINKEDIN_ACCESS_TOKEN', access_token)
    print(".env file updated with LinkedIn Access Token.")

    # --- Step 3: Use Access Token to Get User ID ---

    # Define the userinfo endpoint, which provides user details based on the OpenID scopes.
    userinfo_url = 'https://api.linkedin.com/v2/userinfo'
    # Prepare the headers for the GET request, including the new access token.
    headers = {'Authorization': f'Bearer {access_token}'}
    # Make the GET request to get user information.
    userinfo_response = requests.get(userinfo_url, headers=headers)

    # Check if the user info request was successful.
    if userinfo_response.status_code == 200:
        userinfo_data = userinfo_response.json()
        # The 'sub' field is the "subject" of the token, which is the user's unique, stable ID.
        # This is the correct, programmatic way to get the user's ID.
        linkedin_sub = userinfo_data.get('sub')
        print("LinkedIn User ID (sub):", linkedin_sub)

        # Construct the author URN in the format required by the posting API ('urn:li:person:{ID}').
        linkedin_author_urn = f'urn:li:person:{linkedin_sub}'
        # Automatically save the fully formatted author URN to the .env file.
        set_key('.env', 'LINKEDIN_AUTHOR', linkedin_author_urn)
        print(".env file updated with LinkedIn User ID (sub).")
    else:
        # Handle errors if the user info could not be retrieved.
        print("Failed to retrieve LinkedIn User ID (sub). Error:", userinfo_response.text)
else:
    # Handle errors if the access token could not be retrieved.
    print("Failed to retrieve Access Token. Error:", response.text)