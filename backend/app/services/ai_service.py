
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_client = None


def generate_text(prompt: str) -> str:
    global _client

    if not API_KEY or API_KEY == "your_actual_gemini_api_key":
        return (
            "AI is not configured. Add your Gemini API key to backend/.env "
            "and restart the backend."
        )

    try:
        if _client is None:
            _client = genai.Client(api_key=API_KEY)

        response = _client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )

        return response.text or "The AI returned an empty response."

    except Exception as exc:
        print(f"Gemini API error: {type(exc).__name__}: {exc}")
        return (
            "The AI service is temporarily unavailable. "
            "Check the backend terminal and try again."
        )
