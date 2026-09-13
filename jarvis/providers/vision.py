from __future__ import annotations

import base64
import re
from pathlib import Path

import httpx

from ..config import Settings

GEMINI_MODELS = (
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.0-flash-001",
    "gemini-3-flash-preview",
)


def describe_image(path: Path, prompt: str, settings: Settings) -> str:
    if not path.exists() or path.stat().st_size < 200:
        return "CAPTURA_FALLIDA: no hay un frame válido."
    errors: list[str] = []
    if settings.gemini_api_key:
        try:
            return _gemini(path, prompt, settings)
        except Exception as exc:
            errors.append(f"gemini: {_redact(exc)}")
    if settings.groq_api_key:
        try:
            return _groq_vision(path, prompt, settings)
        except Exception as exc:
            errors.append(f"groq: {_redact(exc)}")
    if errors:
        return "VISION_FALLIDA: " + " | ".join(errors)
    return "No hay proveedor de visión (GEMINI_API_KEY o GROQ_API_KEY)."


def _gemini(path: Path, prompt: str, settings: Settings) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt or "Describe con precisión lo que ves."},
                {"inline_data": {"mime_type": mime, "data": base64.b64encode(path.read_bytes()).decode("ascii")}},
            ]
        }]
    }
    models = [settings.gemini_vision_model, *GEMINI_MODELS]
    last = "sin intentos"
    seen: set[str] = set()
    for model in models:
        if not model or model in seen:
            continue
        seen.add(model)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        response = httpx.post(
            url,
            headers={"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=90,
        )
        if response.status_code == 404:
            last = f"{model} 404"
            continue
        response.raise_for_status()
        parts = (((response.json().get("candidates") or [{}])[0].get("content") or {}).get("parts")) or []
        text = "".join(part.get("text", "") for part in parts).strip()
        return text or "No vi nada útil."
    raise RuntimeError(last)


def _groq_vision(path: Path, prompt: str, settings: Settings) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "temperature": 0.2,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt or "Describe what you see."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
    }
    response = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.groq_api_key}"},
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    return (response.json()["choices"][0]["message"].get("content") or "").strip() or "No vi nada útil."


def _redact(exc: object) -> str:
    text = str(exc)
    text = re.sub(r"key=[^&\s'\"]+", "key=REDACTED", text)
    text = re.sub(r"Bearer [A-Za-z0-9._\-]+", "Bearer REDACTED", text)
    text = re.sub(r"AQ\.[A-Za-z0-9_\-]+", "AQ.REDACTED", text)
    text = re.sub(r"AIza[A-Za-z0-9_\-]+", "AIzaREDACTED", text)
    return text[:240]
