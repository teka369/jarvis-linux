from __future__ import annotations

import shlex
from pathlib import Path

from .config import Settings

HOME = Path.home()


class SafetyError(RuntimeError):
    pass


def assert_safe_command(command: str, settings: Settings) -> list[str]:
    text = command.strip()
    if not text:
        raise SafetyError("Comando vacío.")
    lowered = text.lower()
    for pattern in settings.forbidden_patterns:
        if pattern.lower() in lowered:
            raise SafetyError(f"Comando bloqueado por seguridad: {pattern}")
    try:
        parts = shlex.split(text)
    except ValueError as exc:
        raise SafetyError(f"No pude parsear el comando: {exc}") from exc
    if not parts:
        raise SafetyError("Comando vacío.")
    binary = Path(parts[0]).name
    if settings.allowed_bins and binary not in settings.allowed_bins:
        raise SafetyError(
            f"'{binary}' no está en la lista blanca. Agrégalo en config.yaml si lo necesitas."
        )
    return parts


def assert_safe_path(path: str) -> Path:
    target = Path(path).expanduser().resolve()
    try:
        target.relative_to(HOME)
    except ValueError as exc:
        raise SafetyError("Solo puedo escribir archivos dentro de tu home.") from exc
    return target
