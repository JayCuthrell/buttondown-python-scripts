import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configurations ---
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")

# Replace 'YOUR_ACCESS_TOKEN' with your actual LinkedIn access token
access_token = LINKEDIN_ACCESS_TOKEN

# Set the API endpoint
url = 'https://api.linkedin.com/v2/me?projection=(id)'

# Set the headers
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

# Make the GET request
response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    data = response.json()
    print(f"Your member ID is: urn:li:member:{data['id']}")
else:
    print(f"Error: {response.status_code} - {response.text}")