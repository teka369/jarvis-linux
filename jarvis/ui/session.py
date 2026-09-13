from __future__ import annotations

import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from ..agent import reply
from ..audio.player import speak
from ..config import Settings, load_settings
from ..core.events import AvatarState, BUS
from ..core.log import log
from ..providers.stt import transcribe
from .hotkey import start_ptt_watch
from .ipc import Server
from .notify import toast
from .overlay import run_overlay


class Session:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.history: list[dict[str, str]] = []
        self._busy = threading.Lock()
        self._app = None
        self._win = None
        self._server = Server(self._on_ipc)
        self._ptt_stop = threading.Event()
        self._ptt_thread: threading.Thread | None = None
        self._ptt_chunks: list[np.ndarray] = []
        self._ptt_rate = settings.sample_rate

    def start(self) -> int:
        result = run_overlay(self.toggle_ptt, self.quit)
        if result == 2:
            return 2
        self._app, self._win = result
        self._server.start()
        from PySide6.QtCore import QTimer
        timer = QTimer()
        timer.timeout.connect(self._server.poll)
        timer.start(80)
        watching = start_ptt_watch(self.ptt_start, self.ptt_stop)
        msg = "Mantén Meta+Shift+J para hablar." if watching else "PTT: instala python-evdev y entra al grupo input."
        toast(self.settings.name, msg)
        code = self._app.exec()
        self._server.close()
        return int(code or 0)

    def quit(self) -> None:
        self._ptt_stop.set()
        BUS.set_state(AvatarState.HIDDEN)
        if self._app:
            self._app.quit()

    def ptt_start(self) -> None:
        if self._ptt_thread and self._ptt_thread.is_alive():
            return
        if self._busy.locked():
            return
        self._ptt_stop.clear()
        self._ptt_chunks = []
        BUS.set_state(AvatarState.LISTENING)
        self._ptt_thread = threading.Thread(target=self._ptt_capture, daemon=True)
        self._ptt_thread.start()

    def ptt_stop(self) -> None:
        if not self._ptt_thread:
            return
        self._ptt_stop.set()

    def toggle_ptt(self) -> None:
        if self._ptt_thread and self._ptt_thread.is_alive():
            self.ptt_stop()
        else:
            self.ptt_start()

    def trigger_listen(self) -> None:
        self.toggle_ptt()

    def _on_ipc(self, cmd: str, _data: dict) -> None:
        if cmd == "ping":
            return
        if cmd in {"ptt-start", "listen", "trigger"}:
            self.ptt_start()
        elif cmd in {"ptt-stop", "once"}:
            self.ptt_stop()
        elif cmd == "hide":
            BUS.set_state(AvatarState.HIDDEN)
            if self._win:
                self._win.hide()
        elif cmd == "show":
            BUS.set_state(AvatarState.IDLE)
            if self._win:
                self._win.show()
        elif cmd in {"quit", "stop"}:
            self.quit()

    def _ptt_capture(self) -> None:
        rate = self._ptt_rate
        block = int(rate * 0.02)
        started = time.time()
        try:
            with sd.InputStream(samplerate=rate, channels=1, dtype="float32", blocksize=block) as stream:
                while not self._ptt_stop.is_set() and time.time() - started < 30:
                    data, _ = stream.read(block)
                    self._ptt_chunks.append(np.squeeze(data).astype(np.float32, copy=False))
        except Exception as exc:
            log("ERROR", detail=f"ptt capture: {exc}")
            BUS.set_state(AvatarState.ERROR)
            return
        if not self._busy.acquire(blocking=False):
            return
        try:
            self._process_chunks()
        finally:
            self._ptt_thread = None
            if self._busy.locked():
                self._busy.release()

    def _process_chunks(self) -> None:
        if not self._ptt_chunks:
            BUS.set_state(AvatarState.IDLE)
            return
        audio = np.concatenate(self._ptt_chunks)
        self._ptt_chunks = []
        if audio.size < self._ptt_rate * 0.18:
            BUS.set_state(AvatarState.IDLE)
            return
        wav = Path(tempfile.mkstemp(suffix=".wav")[1])
        pcm = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(wav), "wb") as fh:
            fh.setnchannels(1)
            fh.setsampwidth(2)
            fh.setframerate(self._ptt_rate)
            fh.writeframes(pcm.tobytes())
        try:
            BUS.set_state(AvatarState.THINKING)
            text = transcribe(wav, self.settings)
            log("INPUT", text=text)
            if not text.strip():
                BUS.set_state(AvatarState.IDLE)
                return
            BUS.set_state(AvatarState.EXECUTING)
            spoken = reply(text, self.settings, self.history)
            self.history.append({"role": "user", "content": text})
            self.history.append({"role": "assistant", "content": spoken})
            BUS.set_state(AvatarState.SPEAKING)
            speak(spoken, self.settings)
            BUS.set_state(AvatarState.IDLE)
        except Exception as exc:
            log("ERROR", detail=str(exc))
            BUS.set_state(AvatarState.ERROR)
            toast("Jarvis", str(exc)[:180])
        finally:
            wav.unlink(missing_ok=True)


def run_ui() -> int:
    return Session(load_settings()).start()
