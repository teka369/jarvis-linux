from __future__ import annotations

from typing import Any, Iterable

from ..config import Settings
from ..core.log import log
from ..core.permissions import evaluate
from .base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def register_all(self, tools: Iterable[Tool]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def openai_tools(self) -> list[dict[str, Any]]:
        return [t.openai_schema() for t in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any], settings: Settings) -> str:
        tool = self._tools.get(name)
        if not tool:
            log("ERROR", tool=name, detail="unknown tool")
            return f"Herramienta desconocida: {name}"
        confirmed = bool(arguments.get("confirmed") or arguments.get("confirm"))
        decision = evaluate(
            tool.capabilities,
            camera_enabled=settings.camera_enabled,
            allow_shell=settings.allow_shell,
            confirmed=confirmed,
            auto_confirm=settings.auto_confirm,
        )
        log(
            "PERMISSION",
            tool=name,
            allowed=decision.allowed,
            needs_confirmation=decision.needs_confirmation,
            reason=decision.reason,
        )
        if decision.needs_confirmation:
            return f"CONFIRMATION_REQUIRED: {decision.reason}"
        if not decision.allowed:
            return f"PERMISO_DENEGADO: {decision.reason}"
        log("TOOL_CALL", tool=name, args=_safe_args(arguments))
        try:
            result = tool.handler(arguments or {}, settings)
        except Exception as exc:  # noqa: BLE001
            log("ERROR", tool=name, detail=str(exc))
            return f"Error en {name}: {exc}"
        log("RESULT", tool=name, result=str(result)[:400])
        return result


def _safe_args(arguments: dict[str, Any]) -> dict[str, Any]:
    redacted = {}
    for key, value in (arguments or {}).items():
        if key.lower() in {"content", "text", "body"} and isinstance(value, str) and len(value) > 200:
            redacted[key] = value[:200] + "…"
        else:
            redacted[key] = value
    return redacted
