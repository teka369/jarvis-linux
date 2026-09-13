from __future__ import annotations

import re

from .config import Settings
from .providers.llm import complete
from .tools.desktop import execute_tool


def strip_wake(text: str, settings: Settings) -> str:
    lowered = text.strip()
    for word in settings.wake_words:
        pattern = rf"^\s*{re.escape(word)}[,:\s]+"
        lowered = re.sub(pattern, "", lowered, flags=re.IGNORECASE)
    return lowered.strip() or text.strip()


def contains_wake(text: str, settings: Settings) -> bool:
    blob = text.lower()
    return any(word in blob for word in settings.wake_words)


def reply(user_text: str, settings: Settings, history: list[dict[str, str]]) -> str:
    clean = strip_wake(user_text, settings)
    messages = [
        {
            "role": "system",
            "content": (
                settings.personality
                + "\nResponde en español, máximo 3 frases, salvo que pida un archivo o un comando."
                + " Usa herramientas cuando haya que abrir apps, URLs, escribir archivos,"
                + " mirar la cámara o la pantalla."
            ),
        },
        *history[-8:],
        {"role": "user", "content": clean},
    ]
    result = complete(messages, settings)
    observations: list[str] = []
    for call in result.get("tools") or []:
        name = call.get("name") or ""
        args = call.get("arguments") or {}
        observations.append(f"{name}: {execute_tool(name, args, settings)}")
    if observations:
        follow = complete(
            [
                *messages,
                {
                    "role": "assistant",
                    "content": result.get("text") or "",
                },
                {
                    "role": "user",
                    "content": "Resultado de las herramientas:\n" + "\n".join(observations),
                },
            ],
            settings,
        )
        spoken = follow.get("text") or " ".join(observations)
    else:
        spoken = result.get("text") or ""
    return spoken.strip() or "Listo."
