import os

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.prompts import SYSTEM_PROMPT
from src.schema import TriageResult


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except (FileNotFoundError, KeyError):
        api_key = None

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY is not configured. "
        "Set it in your local .env file or Streamlit secrets."
    )

client = genai.Client(api_key=api_key)


def triage_with_llm(ticket: dict) -> TriageResult:
    """
    Send one support ticket to Gemini
    and return a validated TriageResult.
    """

    prompt = f"""
{SYSTEM_PROMPT}

Customer support ticket:

Ticket ID: {ticket["id"]}
Message: {ticket["message"]}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TriageResult,
        ),
    )

    return TriageResult.model_validate_json(response.text)
