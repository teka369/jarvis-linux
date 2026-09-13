from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path.home() / ".local" / "share" / "jarvis-linux" / "logs"
LOG_FILE = LOG_DIR / "jarvis.log"

_configured = False


def _setup() -> None:
    global _configured
    if _configured:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger("jarvis")
    root.setLevel(logging.INFO)
    if not root.handlers:
        root.addHandler(handler)
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(stream)
    _configured = True


def log(event: str, **fields: object) -> None:
    _setup()
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event.upper(),
        **{k: v for k, v in fields.items() if v is not None},
    }
    logging.getLogger("jarvis").info(json.dumps(payload, ensure_ascii=False, default=str))
