from __future__ import annotations

import base64
from pathlib import Path

import httpx

from ..config import Settings


def describe_image(path: Path, prompt: str, settings: Settings) -> str:
    if not settings.gemini_api_key:
        return "No hay GEMINI_API_KEY para visión."
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt or "Describe con precisión lo que ves."},
                    {
                        "inline_data": {
                            "mime_type": mime,
                            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                        }
                    },
                ]
            }
        ]
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_vision_model}:generateContent?key={settings.gemini_api_key}"
    )
    response = httpx.post(url, json=payload, timeout=90)
    response.raise_for_status()
    parts = (
        ((response.json().get("candidates") or [{}])[0].get("content") or {}).get("parts")
    ) or []
    return "".join(part.get("text", "") for part in parts).strip() or "No vi nada útil."
