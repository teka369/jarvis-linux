from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from .agent import contains_wake, reply
from .audio.player import speak
from .audio.recorder import record_utterance
from .config import load_settings
from .core.events import AvatarState, BUS
from .providers.stt import transcribe
from .ui import ipc
from .ui.notify import toast


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jarvis")
    parser.add_argument(
        "mode",
        nargs="?",
        default="listen",
        choices=["listen", "once", "text", "doctor", "ui", "trigger", "hide", "show", "stop-ui"],
    )
    parser.add_argument("prompt", nargs="*", help="Texto para el modo text")
    args = parser.parse_args(argv)
    settings = load_settings()
    if args.mode == "doctor":
        return _doctor(settings)
    if args.mode == "ui":
        from .ui.session import run_ui
        return run_ui()
    if args.mode == "trigger":
        if ipc.is_running():
            ipc.send("listen")
            return 0
        subprocess.Popen([sys.executable, "-m", "jarvis", "ui"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 0
    if args.mode == "hide":
        return 0 if ipc.send("hide") else 1
    if args.mode == "show":
        return 0 if ipc.send("show") else 1
    if args.mode == "stop-ui":
        return 0 if ipc.send("quit") else 1
    if args.mode == "text":
        text = " ".join(args.prompt).strip()
        if not text:
            print("Uso: jarvis text abre firefox")
            return 2
        BUS.set_state(AvatarState.THINKING)
        spoken = reply(text, settings, [])
        print(spoken)
        BUS.set_state(AvatarState.SPEAKING)
        speak(spoken, settings)
        BUS.set_state(AvatarState.IDLE)
        return 0
    if args.mode == "once":
        if ipc.is_running():
            ipc.send("listen")
            return 0
        return _turn(settings, require_wake=False, history=[])
    history: list[dict[str, str]] = []
    toast(settings.name, "En línea. Di Jarvis o pulsa Meta+Shift+J.")
    print("Jarvis escuchando. Ctrl+C para salir.")
    try:
        while True:
            _turn(settings, require_wake=True, history=history)
    except KeyboardInterrupt:
        print("\nHasta luego.")
        return 0


def _turn(settings, require_wake: bool, history: list[dict[str, str]]) -> int:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = Path(tmp.name)
    try:
        BUS.set_state(AvatarState.LISTENING)
        if not require_wake:
            toast(settings.name, "Te escucho.")
        record_utterance(settings, wav, primed=not require_wake)
        if wav.stat().st_size < 1000:
            BUS.set_state(AvatarState.IDLE)
            return 0
        BUS.set_state(AvatarState.THINKING)
        text = transcribe(wav, settings)
        print(f"Tú: {text}")
        if require_wake and not contains_wake(text, settings):
            BUS.set_state(AvatarState.IDLE)
            return 0
        toast(settings.name, text)
        BUS.set_state(AvatarState.EXECUTING)
        spoken = reply(text, settings, history)
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": spoken})
        print(f"{settings.name}: {spoken}")
        BUS.set_state(AvatarState.SPEAKING)
        speak(spoken, settings)
        BUS.set_state(AvatarState.IDLE)
        return 0
    except Exception as exc:
        BUS.set_state(AvatarState.ERROR)
        toast("Jarvis", str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        wav.unlink(missing_ok=True)


def _doctor(settings) -> int:
    print(f"Nombre: {settings.name}")
    print(f"Voz: {settings.tts_voice}")
    print(f"GROQ: {'sí' if settings.groq_api_key else 'no'}")
    print(f"GEMINI: {'sí' if settings.gemini_api_key else 'no'}")
    print(f"UI running: {'sí' if ipc.is_running() else 'no'}")
    try:
        import PySide6  # noqa: F401
        print("PySide6: sí")
    except ImportError:
        print("PySide6: no  (sudo pacman -S pyside6)")
    from .vision.camera import probe
    info = probe()
    print(f"ffmpeg: {'sí' if info['ffmpeg'] else 'no'}")
    if info["devices"]:
        for cam in info["devices"]:
            print(f"  camera {cam['path']}  {cam['name']}")
    print("OK")
    return 0
