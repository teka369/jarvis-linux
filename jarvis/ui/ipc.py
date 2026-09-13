from __future__ import annotations

import json
import socket
from pathlib import Path

SOCK = Path.home() / ".cache" / "jarvis-linux" / "ui.sock"


def _ensure() -> None:
    SOCK.parent.mkdir(parents=True, exist_ok=True)


def send(command: str, **payload: object) -> bool:
    _ensure()
    if not SOCK.exists():
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.6)
            sock.connect(str(SOCK))
            sock.sendall(json.dumps({"cmd": command, **payload}).encode("utf-8"))
        return True
    except OSError:
        try:
            SOCK.unlink()
        except OSError:
            pass
        return False


def is_running() -> bool:
    return send("ping")


class Server:
    def __init__(self, on_command) -> None:
        self.on_command = on_command
        self._sock: socket.socket | None = None

    def start(self) -> None:
        _ensure()
        if SOCK.exists():
            try:
                SOCK.unlink()
            except OSError:
                pass
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(str(SOCK))
        self._sock.listen(8)
        self._sock.setblocking(False)

    def poll(self) -> None:
        if not self._sock:
            return
        try:
            conn, _ = self._sock.accept()
        except BlockingIOError:
            return
        with conn:
            raw = conn.recv(4096)
        if not raw:
            return
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return
        self.on_command(str(data.get("cmd") or ""), data)

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        try:
            SOCK.unlink()
        except OSError:
            pass
