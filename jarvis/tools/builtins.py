from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.memory import Memory
from ..core.permissions import Capability
from ..providers.vision import describe_image
from ..safety import SafetyError, assert_safe_command, assert_safe_path
from ..vision.camera import CameraError, capture_frame, list_cameras, probe
from .base import Tool

CACHE = Path.home() / ".cache" / "jarvis-linux"
MEMORY = Memory()


def all_tools() -> list[Tool]:
    return [
        Tool("open_url", "Abre una URL en el navegador.", {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, [Capability.NETWORK, Capability.EXECUTE], _open_url),
        Tool("open_app", "Abre una aplicación (firefox, kate, dolphin, konsole, code...).", {"type": "object", "properties": {"app": {"type": "string"}, "args": {"type": "string"}}, "required": ["app"]}, [Capability.EXECUTE], _open_app),
        Tool("close_app", "Cierra una aplicación por nombre de proceso (pkill -x).", {"type": "object", "properties": {"app": {"type": "string"}, "confirmed": {"type": "boolean"}}, "required": ["app"]}, [Capability.EXECUTE, Capability.SYSTEM], _close_app),
        Tool("run_command", "Ejecuta un comando de la lista blanca.", {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}, [Capability.EXECUTE, Capability.SYSTEM], _run_command),
        Tool("write_file", "Crea o sobrescribe un archivo dentro del home.", {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}, [Capability.WRITE], _write_file),
        Tool("read_file", "Lee un archivo de texto del home (máx 8KB).", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, [Capability.READ], _read_file),
        Tool("list_dir", "Lista un directorio del home.", {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, [Capability.READ], _list_dir),
        Tool("delete_path", "Elimina un archivo del home. Requiere confirmed=true.", {"type": "object", "properties": {"path": {"type": "string"}, "confirmed": {"type": "boolean"}}, "required": ["path"]}, [Capability.WRITE, Capability.DESTRUCTIVE], _delete_path),
        Tool("look_camera", "Captura un frame de la webcam y lo analiza. No afirma ver si falla la captura.", {"type": "object", "properties": {"prompt": {"type": "string"}}}, [Capability.CAMERA, Capability.NETWORK], _look_camera),
        Tool("camera_status", "Lista cámaras detectadas y dependencias, sin capturar.", {"type": "object", "properties": {}}, [Capability.READ], _camera_status),
        Tool("screenshot", "Captura la pantalla y la describe.", {"type": "object", "properties": {"prompt": {"type": "string"}}}, [Capability.READ, Capability.NETWORK], _screenshot),
        Tool("notify", "Notificación de escritorio.", {"type": "object", "properties": {"title": {"type": "string"}, "body": {"type": "string"}}, "required": ["body"]}, [Capability.SYSTEM], _notify),
        Tool("system_status", "CPU load, RAM y hora.", {"type": "object", "properties": {}}, [Capability.READ, Capability.SYSTEM], _system_status),
        Tool("set_volume", "Cambia el volumen Pulse/PipeWire (0-150).", {"type": "object", "properties": {"percent": {"type": "integer"}}, "required": ["percent"]}, [Capability.SYSTEM], _set_volume),
        Tool("media_control", "play/pause/next/previous con playerctl.", {"type": "object", "properties": {"action": {"type": "string", "enum": ["play", "pause", "next", "previous", "stop"]}}, "required": ["action"]}, [Capability.SYSTEM], _media),
        Tool("remember", "Guarda un hecho en memoria de largo plazo.", {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}}, "required": ["key", "value"]}, [Capability.WRITE], _remember),
        Tool("recall", "Recupera hechos de la memoria de largo plazo.", {"type": "object", "properties": {"key": {"type": "string"}}}, [Capability.READ], _recall),
    ]


def _open_url(args: dict[str, Any], settings: Any) -> str:
    url = str(args.get("url") or "").strip()
    if not url:
        return "Falta la URL."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    browser = settings.default_browser
    cmd = [browser, url] if shutil.which(browser) else ["xdg-open", url]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Abrí {url}"


def _open_app(args: dict[str, Any], settings: Any) -> str:
    app = str(args.get("app") or "").strip()
    extra = str(args.get("args") or "").strip()
    command = app if not extra else f"{app} {extra}"
    parts = assert_safe_command(command, settings)
    subprocess.Popen(parts, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Lancé {parts[0]}"


def _close_app(args: dict[str, Any], settings: Any) -> str:
    app = Path(str(args.get("app") or "")).name
    if not app:
        return "Falta el nombre de la app."
    if "pkill" not in settings.allowed_bins:
        raise SafetyError("pkill no está en la lista blanca")
    completed = subprocess.run(["pkill", "-x", app], capture_output=True, text=True)
    if completed.returncode == 0:
        return f"Cerré {app}"
    return f"No encontré el proceso {app}"


def _run_command(args: dict[str, Any], settings: Any) -> str:
    parts = assert_safe_command(str(args.get("command") or ""), settings)
    completed = subprocess.run(parts, capture_output=True, text=True, timeout=20)
    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        return f"Falló ({completed.returncode}): {output[:600]}"
    return output[:800] or "Listo."


def _write_file(args: dict[str, Any], _settings: Any) -> str:
    path = assert_safe_path(str(args.get("path") or ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(args.get("content") or ""), encoding="utf-8")
    return f"Escribí {path}"


def _read_file(args: dict[str, Any], _settings: Any) -> str:
    path = assert_safe_path(str(args.get("path") or ""))
    if not path.exists():
        return f"No existe {path}"
    return path.read_text(encoding="utf-8", errors="replace")[:8192]


def _list_dir(args: dict[str, Any], _settings: Any) -> str:
    path = assert_safe_path(str(args.get("path") or ""))
    if not path.is_dir():
        return f"No es un directorio: {path}"
    names = sorted(p.name for p in path.iterdir())[:80]
    return "\n".join(names) or "(vacío)"


def _delete_path(args: dict[str, Any], _settings: Any) -> str:
    path = assert_safe_path(str(args.get("path") or ""))
    if path.is_dir():
        return "Por seguridad no borro directorios en esta versión."
    if not path.exists():
        return f"No existe {path}"
    path.unlink()
    return f"Eliminé {path}"


def _look_camera(args: dict[str, Any], settings: Any) -> str:
    try:
        frame = capture_frame(device=settings.camera_device)
    except CameraError as exc:
        return f"CAPTURA_FALLIDA: {exc}"
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "-a", "Jarvis", "Cámara", f"Frame capturado: {frame}"], check=False)
    prompt = str(args.get("prompt") or "Describe con precisión lo que hay en esta foto.")
    return f"Frame: {frame}\n{describe_image(frame, prompt, settings)}"


def _camera_status(_args: dict[str, Any], settings: Any) -> str:
    info = probe()
    info["enabled"] = settings.camera_enabled
    info["configured_device"] = settings.camera_device
    return json.dumps(info, ensure_ascii=False)


def _screenshot(args: dict[str, Any], settings: Any) -> str:
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


def _notify(args: dict[str, Any], settings: Any) -> str:
    title = str(args.get("title") or settings.name)
    body = str(args.get("body") or "")
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", title, body], check=False)
    return "Notificación enviada."


def _system_status(_args: dict[str, Any], _settings: Any) -> str:
    return json.dumps({"load": os.getloadavg(), "memory": _read_mem(), "time": datetime.now().isoformat(timespec="seconds"), "user": os.environ.get("USER"), "cameras": [c.path for c in list_cameras()]}, ensure_ascii=False)


def _set_volume(args: dict[str, Any], _settings: Any) -> str:
    percent = max(0, min(150, int(args.get("percent") or 0)))
    if not shutil.which("pactl"):
        return "No está pactl."
    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"], check=False)
    return f"Volumen {percent}%"


def _media(args: dict[str, Any], _settings: Any) -> str:
    action = str(args.get("action") or "")
    if not shutil.which("playerctl"):
        return "Instala playerctl."
    subprocess.run(["playerctl", action], check=False)
    return f"Media: {action}"


def _remember(args: dict[str, Any], _settings: Any) -> str:
    return MEMORY.remember(str(args.get("key") or ""), str(args.get("value") or ""))


def _recall(args: dict[str, Any], _settings: Any) -> str:
    key = args.get("key")
    return MEMORY.recall(str(key) if key else None)


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
