from __future__ import annotations

import threading
from pathlib import Path
import tempfile

from ..agent import reply
from ..audio.player import speak
from ..audio.recorder import record_utterance
from ..config import Settings, load_settings
from ..core.events import AvatarState, BUS
from ..core.log import log
from ..providers.stt import transcribe
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

    def start(self) -> int:
        result = run_overlay(self.trigger_listen, self.quit)
        if result == 2:
            return 2
        self._app, self._win = result
        self._server.start()
        from PySide6.QtCore import QTimer
        timer = QTimer()
        timer.timeout.connect(self._server.poll)
        timer.start(80)
        toast(self.settings.name, "Núcleo en línea. Meta+Shift+J para hablar.")
        code = self._app.exec()
        self._server.close()
        return int(code or 0)

    def quit(self) -> None:
        BUS.set_state(AvatarState.HIDDEN)
        if self._app:
            self._app.quit()

    def trigger_listen(self) -> None:
        if not self._busy.acquire(blocking=False):
            return
        threading.Thread(target=self._turn, daemon=True).start()

    def _on_ipc(self, cmd: str, _data: dict) -> None:
        if cmd == "ping":
            return
        if cmd in {"listen", "trigger", "once"}:
            self.trigger_listen()
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

    def _turn(self) -> None:
        settings = self.settings
        try:
            BUS.set_state(AvatarState.LISTENING)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav = Path(tmp.name)
            record_utterance(settings, wav, primed=True)
            if wav.stat().st_size < 1000:
                BUS.set_state(AvatarState.IDLE)
                return
            BUS.set_state(AvatarState.THINKING)
            text = transcribe(wav, settings)
            log("INPUT", text=text)
            wav.unlink(missing_ok=True)
            if not text.strip():
                BUS.set_state(AvatarState.IDLE)
                return
            BUS.set_state(AvatarState.EXECUTING)
            spoken = reply(text, settings, self.history)
            self.history.append({"role": "user", "content": text})
            self.history.append({"role": "assistant", "content": spoken})
            BUS.set_state(AvatarState.SPEAKING)
            speak(spoken, settings)
            BUS.set_state(AvatarState.IDLE)
        except Exception as exc:
            log("ERROR", detail=str(exc))
            BUS.set_state(AvatarState.ERROR)
            toast("Jarvis", str(exc)[:180])
        finally:
            if self._busy.locked():
                self._busy.release()


def run_ui() -> int:
    return Session(load_settings()).start()
