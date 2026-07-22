#app/nid_extractor.py
import io
import json
import os
from typing import Optional
from fastapi import HTTPException
from google import genai
from google.genai import types
from PIL import Image

MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
_client: Optional[genai.Client] = None

IMG_MAX_DIMENSION = int(os.environ.get("IMG_MAX_DIMENSION", "1024"))
IMG_QUALITY = int(os.environ.get("IMG_QUALITY", "80"))


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")
        _client = genai.Client(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You read Bangladesh National ID (NID) cards. You are given the FRONT and BACK images of one card.
Extract these fields and translate any Bengali text into natural, meaning-preserving English:
- name (full name)
- fatherName
- motherName
- dateOfBirth (format YYYY-MM-DD if determinable, else as printed)
- nidNumber (digits only)
- address (natural English address ordering)

Return ONLY raw JSON, no markdown, no commentary, exactly this shape (use null for anything you cannot read):
{
  "name": string|null,
  "fatherName": string|null,
  "motherName": string|null,
  "dateOfBirth": string|null,
  "nidNumber": string|null,
  "address": string|null,
  "isValidNid": boolean,
  "sidesSwapped": boolean
}
Never invent data. If a field is unreadable on both images, return null.
If either image does NOT appear to be a Bangladesh NID card, set "isValidNid": false and leave other fields null.
The FRONT typically shows a photo, name, father's/mother's name, date of birth, and NID number.
The BACK typically shows the address and a barcode/QR code.
If the image labeled FRONT actually looks like the back (or vice versa), set "sidesSwapped": true."""


def _compress_image(raw: bytes) -> bytes:
    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")

    width, height = img.size
    if max(width, height) > IMG_MAX_DIMENSION:
        scale = IMG_MAX_DIMENSION / max(width, height)
        img = img.resize((int(width * scale), int(height * scale)), Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=IMG_QUALITY, optimize=True)
    return buffer.getvalue()


def extract_nid_data(front_bytes: bytes, front_name: str, back_bytes: bytes, back_name: str) -> dict:
    client = get_client()

    front_bytes = _compress_image(front_bytes)
    back_bytes = _compress_image(back_bytes)

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                SYSTEM_PROMPT,
                "FRONT of the NID card:",
                types.Part.from_bytes(data=front_bytes, mime_type="image/jpeg"),
                "BACK of the NID card:",
                types.Part.from_bytes(data=back_bytes, mime_type="image/jpeg"),
                "Extract the fields now and return only the JSON object.",
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
    except Exception as exc:
        if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
            raise HTTPException(status_code=429, detail="Gemini API rate limit reached. Please wait a moment.")
        raise HTTPException(status_code=502, detail=f"Gemini AI service error: {exc}")

    res_text = response.text
    if not res_text:
        raise ValueError("Gemini returned an empty response.")

    cleaned = res_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI returned malformed JSON: {exc}")