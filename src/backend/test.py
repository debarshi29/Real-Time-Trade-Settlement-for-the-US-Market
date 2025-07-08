from dotenv import load_dotenv
load_dotenv()
import os

# === GOOGLE GEMINI API KEY ===
api_key = os.getenv("GOOGLE_API_KEY")
print(api_key)