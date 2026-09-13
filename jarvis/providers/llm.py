from __future__ import annotations

import json
from typing import Any

import httpx

from ..config import Settings

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Abre una URL en el navegador.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Abre una aplicación del escritorio (firefox, kate, dolphin, konsole, code...).",
            "parameters": {
                "type": "object",
                "properties": {"app": {"type": "string"}, "args": {"type": "string"}},
                "required": ["app"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Ejecuta un comando de shell de la lista blanca.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Crea o sobrescribe un archivo dentro del home del usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "look_camera",
            "description": "Toma una foto de la webcam y descríbela.",
            "parameters": {
                "type": "object",
                "properties": {"prompt": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Toma una captura de pantalla y descríbela.",
            "parameters": {
                "type": "object",
                "properties": {"prompt": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify",
            "description": "Muestra una notificación de escritorio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_status",
            "description": "Devuelve CPU, RAM, disco y uptime.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class ProviderError(RuntimeError):
    pass


def complete(messages: list[dict[str, str]], settings: Settings) -> dict[str, Any]:
    errors: list[str] = []
    for name in settings.llm_order:
        try:
            if name == "gemini":
                return _gemini(messages, settings)
            if name == "groq":
                return _openai_compatible(
                    messages,
                    settings,
                    base="https://api.groq.com/openai/v1",
                    key=settings.groq_api_key,
                    model=settings.groq_llm_model,
                )
            if name == "nvidia":
                return _openai_compatible(
                    messages,
                    settings,
                    base="https://integrate.api.nvidia.com/v1",
                    key=settings.nvidia_api_key,
                    model=settings.nvidia_llm_model,
                )
            if name == "openrouter":
                return _openai_compatible(
                    messages,
                    settings,
                    base="https://openrouter.ai/api/v1",
                    key=settings.openrouter_api_key,
                    model=settings.openrouter_llm_model,
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")
    raise ProviderError("LLM falló en todos los proveedores. " + " | ".join(errors))


def _openai_compatible(
    messages: list[dict[str, str]],
    settings: Settings,
    *,
    base: str,
    key: str,
    model: str,
) -> dict[str, Any]:
    if not key:
        raise ProviderError("Falta API key")
    payload = {
        "model": model,
        "temperature": 0.3,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
    }
    response = httpx.post(
        f"{base}/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    choice = response.json()["choices"][0]["message"]
    calls = choice.get("tool_calls") or []
    parsed = []
    for call in calls:
        fn = call.get("function") or {}
        args = fn.get("arguments") or "{}"
        try:
            parsed_args = json.loads(args)
        except json.JSONDecodeError:
            parsed_args = {}
        parsed.append({"name": fn.get("name"), "arguments": parsed_args})
    return {"text": (choice.get("content") or "").strip(), "tools": parsed}


def _gemini(messages: list[dict[str, str]], settings: Settings) -> dict[str, Any]:
    if not settings.gemini_api_key:
        raise ProviderError("Falta GEMINI_API_KEY")
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    contents = []
    for message in messages:
        if message["role"] == "system":
            continue
        role = "user" if message["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": message["content"]}]})
    payload: dict[str, Any] = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.3},
        "tools": [_gemini_tools()],
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_llm_model}:generateContent?key={settings.gemini_api_key}"
    )
    response = httpx.post(url, json=payload, timeout=90)
    response.raise_for_status()
    body = response.json()
    parts = (((body.get("candidates") or [{}])[0].get("content") or {}).get("parts")) or []
    text_bits: list[str] = []
    tools: list[dict[str, Any]] = []
    for part in parts:
        if "text" in part:
            text_bits.append(part["text"])
        fc = part.get("functionCall") or part.get("function_call")
        if fc:
            tools.append({"name": fc.get("name"), "arguments": fc.get("args") or {}})
    return {"text": "\n".join(text_bits).strip(), "tools": tools}


def _gemini_tools() -> dict[str, Any]:
    decls = []
    for tool in TOOLS:
        fn = tool["function"]
        decls.append(
            {
                "name": fn["name"],
                "description": fn["description"],
                "parameters": fn["parameters"],
            }
        )
    return {"function_declarations": decls}
