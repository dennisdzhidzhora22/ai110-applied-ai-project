import os
import time
from dotenv import load_dotenv

GEMINI_MODEL = "gemini-2.5-flash-lite"

_client = None


def _get_client():
    global _client
    if _client is None:
        load_dotenv()
        from google import genai
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def generate(prompt: str, retries: int = 3) -> str:
    """Call Gemini with automatic retry on 503 UNAVAILABLE errors."""
    client = _get_client()
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            if attempt < retries - 1 and "503" in str(e):
                time.sleep(2 ** attempt)
                continue
            raise
