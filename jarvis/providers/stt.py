from __future__ import annotations

import base64
from pathlib import Path

import httpx

from ..config import Settings


class ProviderError(RuntimeError):
    pass


def transcribe(path: Path, settings: Settings) -> str:
    errors: list[str] = []
    for name in settings.stt_order:
        try:
            if name == "groq":
                return _groq(path, settings)
            if name == "gemini":
                return _gemini(path, settings)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")
    raise ProviderError("STT falló en todos los proveedores. " + " | ".join(errors))


def _groq(path: Path, settings: Settings) -> str:
    if not settings.groq_api_key:
        raise ProviderError("Falta GROQ_API_KEY")
    with path.open("rb") as fh:
        files = {"file": (path.name, fh, "audio/wav")}
        data = {
            "model": settings.groq_stt_model,
            "language": "es" if settings.language.startswith("es") else settings.language,
            "response_format": "json",
        }
        response = httpx.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            files=files,
            data=data,
            timeout=60,
        )
    response.raise_for_status()
    text = (response.json().get("text") or "").strip()
    if not text:
        raise ProviderError("Groq devolvió texto vacío")
    return text


def _gemini(path: Path, settings: Settings) -> str:
    if not settings.gemini_api_key:
        raise ProviderError("Falta GEMINI_API_KEY")
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Transcribe este audio en el idioma original. Devuelve solo la transcripción."
                    },
                    {
                        "inline_data": {
                            "mime_type": "audio/wav",
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
    text = _gemini_text(response.json())
    if not text:
        raise ProviderError("Gemini STT vacío")
    return text


def _gemini_text(body: dict) -> str:
    candidates = body.get("candidates") or []
    if not candidates:
        return ""
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    return "".join(part.get("text", "") for part in parts).strip()
