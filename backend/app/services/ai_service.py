"""
Optional Google Gemini integration (lazy-loaded).

The application runs without this package or API key; enable only when
LAWYERAI_USE_LLM=1 and GEMINI_API_KEY are set.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_client = None


def is_configured() -> bool:
    return bool(API_KEY) and API_KEY != "your_actual_gemini_api_key"


def use_llm_for_responses() -> bool:
    return os.getenv("LAWYERAI_USE_LLM", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def generate_text(prompt: str) -> str:
    global _client

    if not is_configured():
        raise RuntimeError("Gemini is not configured.")

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is not installed. Add it to your environment to use LLM mode."
        ) from exc

    if _client is None:
        _client = genai.Client(api_key=API_KEY)

    response = _client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    return response.text or "The AI returned an empty response."
