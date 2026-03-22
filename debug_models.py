import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load secrets
load_dotenv()
api_key = os.getenv("SARVAM_API_KEY")

print(f"--- DIAGNOSTIC START ---")
if not api_key:
    print("ERROR: No API Key found in .env file.")
else:
    print(f"API Key found: {api_key[:5]}... (hidden)")

    # Configure the library
    genai.configure(api_key=api_key)

    try:
        print("\nAttempting to list available models...")
        count = 0
        for m in genai.list_models():
            # We only care about models that can generate content (chat/text)
            if 'generateContent' in m.supported_generation_methods:
                print(f"AVAILABLE MODEL: {m.name}")
                count += 1

        if count == 0:
            print("\nRESULT: Connection successful, but NO models returned.")
            print("This usually means the API Key is restricted in Google Cloud Console.")
        else:
            print(f"\nRESULT: Found {count} usable models.")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")

print("--- DIAGNOSTIC END ---")