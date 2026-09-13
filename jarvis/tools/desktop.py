from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import Settings
from ..providers.vision import describe_image
from ..safety import SafetyError, assert_safe_command, assert_safe_path

CACHE = Path.home() / ".cache" / "jarvis-linux"


def execute_tool(name: str, arguments: dict[str, Any], settings: Settings) -> str:
    handlers = {
        "open_url": _open_url,
        "open_app": _open_app,
        "run_command": _run_command,
        "write_file": _write_file,
        "look_camera": _look_camera,
        "screenshot": _screenshot,
        "notify": _notify,
        "system_status": _system_status,
    }
    handler = handlers.get(name)
    if not handler:
        return f"Herramienta desconocida: {name}"
    try:
        return handler(arguments or {}, settings)
    except SafetyError as exc:
        return f"Bloqueado: {exc}"
    except Exception as exc:  # noqa: BLE001
        return f"Error en {name}: {exc}"


def _open_url(args: dict[str, Any], settings: Settings) -> str:
    url = str(args.get("url") or "").strip()
    if not url:
        return "Falta la URL."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    browser = settings.default_browser
    if shutil.which(browser):
        subprocess.Popen([browser, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Abrí {url}"


def _open_app(args: dict[str, Any], settings: Settings) -> str:
    app = str(args.get("app") or "").strip()
    extra = str(args.get("args") or "").strip()
    command = app if not extra else f"{app} {extra}"
    parts = assert_safe_command(command, settings)
    subprocess.Popen(parts, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Lancé {parts[0]}"


def _run_command(args: dict[str, Any], settings: Settings) -> str:
    if not settings.allow_shell:
        return "El shell está desactivado en config.yaml"
    command = str(args.get("command") or "")
    parts = assert_safe_command(command, settings)
    completed = subprocess.run(parts, capture_output=True, text=True, timeout=20)
    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        return f"Falló ({completed.returncode}): {output[:600]}"
    return output[:800] or "Listo."


def _write_file(args: dict[str, Any], settings: Settings) -> str:
    path = assert_safe_path(str(args.get("path") or ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(args.get("content") or ""), encoding="utf-8")
    return f"Escribí {path}"


def _look_camera(args: dict[str, Any], settings: Settings) -> str:
    dest = CACHE / "camera.jpg"
    CACHE.mkdir(parents=True, exist_ok=True)
    if not shutil.which("ffmpeg"):
        return "Necesito ffmpeg para la cámara."
    completed = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "v4l2",
            "-i",
            "/dev/video0",
            "-frames:v",
            "1",
            str(dest),
        ],
        capture_output=True,
        text=True,
        timeout=12,
    )
    if completed.returncode != 0 or not dest.exists():
        return "No pude acceder a la cámara. Revisa /dev/video0."
    prompt = str(args.get("prompt") or "Describe a la persona y lo que hay frente a la cámara.")
    return describe_image(dest, prompt, settings)


def _screenshot(args: dict[str, Any], settings: Settings) -> str:
    dest = CACHE / "screen.png"
    CACHE.mkdir(parents=True, exist_ok=True)
    if shutil.which("spectacle"):
        subprocess.run(["spectacle", "-b", "-n", "-o", str(dest)], timeout=12, check=False)
    elif shutil.which("grim"):
        subprocess.run(["grim", str(dest)], timeout=12, check=False)
    elif shutil.which("import"):
        subprocess.run(["import", "-window", "root", str(dest)], timeout=12, check=False)
    else:
        return "No encontré spectacle, grim ni imagemagick."
    if not dest.exists():
        return "No pude guardar la captura."
    prompt = str(args.get("prompt") or "Resume lo que se ve en la pantalla.")
    return describe_image(dest, prompt, settings)


def _notify(args: dict[str, Any], settings: Settings) -> str:
    title = str(args.get("title") or settings.name)
    body = str(args.get("body") or "")
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", title, body], check=False)
    return "Notificación enviada."


def _system_status(_args: dict[str, Any], _settings: Settings) -> str:
    load = os.getloadavg()
    mem = _read_mem()
    return json.dumps(
        {
            "load": load,
            "memory": mem,
            "time": datetime.now().isoformat(timespec="seconds"),
            "user": os.environ.get("USER"),
        },
        ensure_ascii=False,
    )


def _read_mem() -> dict[str, int]:
    info: dict[str, int] = {}
    path = Path("/proc/meminfo")
    if not path.exists():
        return info
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(("MemTotal:", "MemAvailable:")):
            key, raw, *_ = line.replace(":", "").split()
            info[key] = int(raw)
    return info
