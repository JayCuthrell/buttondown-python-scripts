import google.generativeai as genai
import os
from dotenv import load_dotenv # Import load_dotenv
import pprint # For pretty printing the model list (optional, for checking models)

# --- Load environment variables from .env file ---
load_dotenv()

# --- Get the API key from the environment (now loaded from .env) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Check if the API key was loaded successfully
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found. Make sure it's set in your .env file or environment variables.")

# --- Configure the Generative AI SDK ---
genai.configure(api_key=GOOGLE_API_KEY)

# --- Verify available models (as suggested by the previous error) ---
print("Listing available models that support 'generateContent':")
found_model = False
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        pprint.pprint(m.name)
        # Assuming you want to use the first suitable Gemini 1.5 model found
        # You might want to be more specific, e.g., by checking for 'gemini-1.5-flash' or 'gemini-1.5-pro'
        if not found_model and ("gemini-1.5-flash" in m.name or "gemini-1.5-pro" in m.name):
            model_name_to_use = m.name
            found_model = True

if not found_model:
    raise ValueError("No suitable Gemini 1.5 model found. Check available models.")
else:
    print(f"\nUsing model: {model_name_to_use}")

# --- Example of using the model ---
try:
    model = genai.GenerativeModel(model_name_to_use) # Use the dynamically found model name
    response = model.generate_content("What is the capital of France?")
    print("\nGenerated Content:")
    print(response.text)

except Exception as e:
    print(f"Error generating content with Gemini: {e}")
