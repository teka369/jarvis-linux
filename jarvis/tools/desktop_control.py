from __future__ import annotations

import shutil
import subprocess
from typing import Any

from ..core.permissions import Capability
from .base import Tool


def extra_desktop_tools() -> list[Tool]:
    return [
        Tool(
            "close_window",
            "Cierra la ventana activa o una por título (Alt+F4 / KWin).",
            {"type": "object", "properties": {"title": {"type": "string"}}},
            [Capability.SYSTEM, Capability.EXECUTE],
            _close_window,
        ),
        Tool(
            "list_windows",
            "Lista ventanas abiertas si kdotool o wmctrl están disponibles.",
            {"type": "object", "properties": {}},
            [Capability.READ, Capability.SYSTEM],
            _list_windows,
        ),
        Tool(
            "scroll_screen",
            "Hace scroll en la ventana activa (ydotool/xdotool). direction=up|down, amount=1-12.",
            {"type": "object", "properties": {"direction": {"type": "string"}, "amount": {"type": "integer"}}},
            [Capability.SYSTEM, Capability.EXECUTE],
            _scroll,
        ),
        Tool(
            "send_keys",
            "Envía atajos a la ventana activa. Ej: alt+F4, ctrl+t, ctrl+l.",
            {"type": "object", "properties": {"keys": {"type": "string"}}, "required": ["keys"]},
            [Capability.SYSTEM, Capability.EXECUTE],
            _send_keys,
        ),
    ]


def _run(cmd: list[str], timeout: int = 8) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _close_window(args: dict[str, Any], _s: Any) -> str:
    title = str(args.get("title") or "").strip()
    if title and shutil.which("kdotool"):
        listed = _run(["kdotool", "search", "--name", title])
        wid = (listed.stdout or "").strip().splitlines()
        if wid:
            _run(["kdotool", "windowclose", wid[0]])
            return f"Cerré la ventana que coincidía con '{title}'."
    if shutil.which("wmctrl") and title:
        r = _run(["wmctrl", "-c", title])
        if r.returncode == 0:
            return f"Cerré '{title}' con wmctrl."
    if shutil.which("ydotool"):
        _run(["ydotool", "key", "56:1", "62:1", "62:0", "56:0"])
        return "Envié Alt+F4 a la ventana activa (ydotool)."
    if shutil.which("xdotool"):
        _run(["xdotool", "getactivewindow", "windowclose"])
        return "Cerré la ventana activa con xdotool."
    if shutil.which("qdbus"):
        _run(["qdbus", "org.kde.kglobalaccel", "/kglobalaccel", "org.kde.kglobalaccel.invoke", "kwin", "Window Close"])
        return "Pedí a KWin cerrar la ventana activa."
    return "No pude cerrar ventanas: instala kdotool o ydotool (Wayland)."


def _list_windows(_args: dict[str, Any], _s: Any) -> str:
    if shutil.which("kdotool"):
        out = _run(["kdotool", "search", ""])
        return (out.stdout or out.stderr or "sin ventanas")[:1200]
    if shutil.which("wmctrl"):
        out = _run(["wmctrl", "-l"])
        return (out.stdout or "sin ventanas")[:1200]
    return "Instala kdotool (AUR) para listar ventanas en Plasma Wayland."


def _scroll(args: dict[str, Any], _s: Any) -> str:
    direction = str(args.get("direction") or "down").lower()
    amount = max(1, min(12, int(args.get("amount") or 3)))
    if shutil.which("ydotool"):
        btn = "5" if direction == "down" else "4"
        for _ in range(amount):
            _run(["ydotool", "click", btn])
        return f"Scroll {direction} x{amount}"
    if shutil.which("xdotool"):
        btn = "5" if direction == "down" else "4"
        _run(["xdotool", "click", "--repeat", str(amount), btn])
        return f"Scroll {direction} x{amount}"
    return "Para scroll en Wayland instala ydotool y el daemon ydotoold."


def _send_keys(args: dict[str, Any], _s: Any) -> str:
    keys = str(args.get("keys") or "").strip()
    if not keys:
        return "Faltan teclas."
    if shutil.which("xdotool"):
        _run(["xdotool", "key", keys.replace("+", "+")])
        return f"Teclas: {keys}"
    if shutil.which("wtype"):
        _run(["wtype", "-k", keys])
        return f"Teclas: {keys}"
    return "Instala xdotool o wtype/ydotool para enviar teclas."
