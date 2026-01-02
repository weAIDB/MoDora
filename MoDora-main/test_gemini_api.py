import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from api_utils import gpt_generate
from constants import MODEL, API_URL

def test_text_generation():
    print(f"Testing Text Generation with Model: {MODEL} at {API_URL}...")
    try:
        response = gpt_generate("Say 'Hello from Gemini' if you can read this.")
        print(f"✅ Success! Response:\n{response}")
    except Exception as e:
        print(f"❌ Failed! Error:\n{e}")

if __name__ == "__main__":
    test_text_generation()
