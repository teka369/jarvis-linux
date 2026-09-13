from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path.home() / ".local" / "share" / "jarvis-linux" / "memory.json"


class Memory:
    """Long-term key/value memory. Short-term lives in the orchestrator history."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = {"facts": {}, "notes": []}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def remember(self, key: str, value: str) -> str:
        self._data.setdefault("facts", {})[key.strip()] = value.strip()
        self._save()
        return f"Guardé {key}."

    def recall(self, key: str | None = None) -> str:
        facts = self._data.get("facts") or {}
        if key:
            return str(facts.get(key, f"No tengo nada sobre {key}."))
        if not facts:
            return "Memoria larga vacía."
        return "\n".join(f"{k}: {v}" for k, v in facts.items())

    def forget(self, key: str) -> str:
        facts = self._data.setdefault("facts", {})
        if key in facts:
            del facts[key]
            self._save()
            return f"Olvidé {key}."
        return f"No estaba {key}."

    def context_block(self) -> str:
        facts = self._data.get("facts") or {}
        if not facts:
            return ""
        lines = [f"- {k}: {v}" for k, v in list(facts.items())[:30]]
        return "Memoria de largo plazo:\n" + "\n".join(lines)
