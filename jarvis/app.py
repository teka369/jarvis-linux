from __future__ import annotations

import argparse
import sys
import tempfile
import threading
from pathlib import Path

from .agent import contains_wake, reply
from .audio.player import speak
from .audio.recorder import record_utterance
from .config import load_settings
from .providers.stt import transcribe
from .ui.notify import toast


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jarvis")
    parser.add_argument(
        "mode",
        nargs="?",
        default="listen",
        choices=["listen", "once", "text", "doctor"],
        help="listen=siempre atento, once=un comando, text=sin micro, doctor=diagnóstico",
    )
    parser.add_argument("prompt", nargs="*", help="Texto para el modo text")
    args = parser.parse_args(argv)
    settings = load_settings()

    if args.mode == "doctor":
        return _doctor(settings)
    if args.mode == "text":
        text = " ".join(args.prompt).strip()
        if not text:
            print("Uso: jarvis text abre firefox")
            return 2
        spoken = reply(text, settings, [])
        print(spoken)
        speak(spoken, settings)
        return 0
    if args.mode == "once":
        return _turn(settings, require_wake=False, history=[])

    history: list[dict[str, str]] = []
    toast(settings.name, "En línea. Di Jarvis o pulsa Super+J.")
    print("Jarvis escuchando. Ctrl+C para salir.")
    if settings.hotkey_enabled:
        threading.Thread(target=_hotkey_loop, args=(settings,), daemon=True).start()
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
        if not require_wake:
            toast(settings.name, "Te escucho.")
        record_utterance(settings, wav, primed=not require_wake)
        if wav.stat().st_size < 1000:
            return 0
        text = transcribe(wav, settings)
        print(f"Tú: {text}")
        if require_wake and not contains_wake(text, settings):
            return 0
        toast(settings.name, text)
        spoken = reply(text, settings, history)
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": spoken})
        print(f"{settings.name}: {spoken}")
        speak(spoken, settings)
        return 0
    except Exception as exc:  # noqa: BLE001
        toast("Jarvis", str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        wav.unlink(missing_ok=True)


def _hotkey_loop(settings) -> None:
    try:
        from pynput import keyboard
    except Exception:
        return

    def on_activate() -> None:
        _turn(settings, require_wake=False, history=[])

    try:
        with keyboard.GlobalHotKeys({settings.hotkey: on_activate}) as listener:
            listener.join()
    except Exception:
        return


def _doctor(settings) -> int:
    print(f"Nombre: {settings.name}")
    print(f"Voz: {settings.tts_voice}")
    print(f"GROQ: {'sí' if settings.groq_api_key else 'no'}")
    print(f"GEMINI: {'sí' if settings.gemini_api_key else 'no'}")
    print(f"NVIDIA: {'sí' if settings.nvidia_api_key else 'no'}")
    print(f"OPENROUTER: {'sí' if settings.openrouter_api_key else 'no'}")
    if not settings.groq_api_key and not settings.gemini_api_key:
        print("Falta al menos GROQ_API_KEY o GEMINI_API_KEY")
        return 1
    print("OK")
    return 0
