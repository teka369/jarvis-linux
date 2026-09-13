from __future__ import annotations

import re

from .config import Settings
from .core.log import log
from .core.memory import Memory
from .providers.llm import complete
from .tools import execute_tool

MEMORY = Memory()


def strip_wake(text: str, settings: Settings) -> str:
    lowered = text.strip()
    for word in settings.wake_words:
        pattern = rf"^\s*{re.escape(word)}[,:\s]+"
        lowered = re.sub(pattern, "", lowered, flags=re.IGNORECASE)
    return lowered.strip() or text.strip()


def contains_wake(text: str, settings: Settings) -> bool:
    blob = text.lower()
    return any(word in blob for word in settings.wake_words)


def _is_confirmation(text: str) -> bool:
    blob = text.lower()
    return any(token in blob for token in ("sí", "si ", "confirma", "adelante", "hazlo", "ok"))


def reply(user_text: str, settings: Settings, history: list[dict[str, str]]) -> str:
    clean = strip_wake(user_text, settings)
    log("INPUT", text=clean)
    memory_block = MEMORY.context_block()
    system = (
        settings.personality
        + "\nResponde en español, máximo 3 frases, salvo archivo o comando."
        + " Usa herramientas para acciones reales."
        + " Si el usuario dice cierra la ventana, usa close_window, no digas que no puedes."
        + " Si habla de 'aquí', 'esto', 'esta pantalla' o 'este archivo', llama screenshot ANTES de preguntar la ruta."
        + " Si pide entrar a una web, usa open_url; si pide bajar o subir, usa scroll_screen."
        + " Ruta por defecto si no hay otra: ~/Escritorio."
        + " Si look_camera o screenshot fallan, dilo; no inventes que viste."
        + " Si una herramienta pide CONFIRMATION_REQUIRED, pregunta confirmación."
    )
    if memory_block:
        system += "\n" + memory_block
    messages = [
        {"role": "system", "content": system},
        *history[-8:],
        {"role": "user", "content": clean},
    ]
    result = complete(messages, settings)
    log("REASONING", text=(result.get("text") or "")[:300], tools=len(result.get("tools") or []))
    observations: list[str] = []
    for call in result.get("tools") or []:
        name = call.get("name") or ""
        args = dict(call.get("arguments") or {})
        if _is_confirmation(clean):
            args["confirmed"] = True
        observations.append(f"{name}: {execute_tool(name, args, settings)}")
    if observations:
        follow = complete(
            [
                *messages,
                {"role": "assistant", "content": result.get("text") or ""},
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
    spoken = spoken.strip() or "Listo."
    log("OUTPUT", text=spoken[:300])
    return spoken
