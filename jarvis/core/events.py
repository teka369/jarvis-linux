from __future__ import annotations

from enum import Enum
from threading import Lock
from typing import Callable


class AvatarState(str, Enum):
    HIDDEN = "hidden"
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    ERROR = "error"


class EventBus:
    def __init__(self) -> None:
        self._state = AvatarState.IDLE
        self._energy = 0.0
        self._lock = Lock()
        self._listeners: list[Callable[[AvatarState, float], None]] = []

    @property
    def state(self) -> AvatarState:
        return self._state

    @property
    def energy(self) -> float:
        return self._energy

    def subscribe(self, fn: Callable[[AvatarState, float], None]) -> None:
        self._listeners.append(fn)

    def set_state(self, state: AvatarState) -> None:
        with self._lock:
            self._state = state
        self._emit()

    def set_energy(self, value: float) -> None:
        with self._lock:
            self._energy = max(0.0, min(1.0, float(value)))
        self._emit()

    def _emit(self) -> None:
        state, energy = self._state, self._energy
        for fn in list(self._listeners):
            try:
                fn(state, energy)
            except Exception:
                pass


BUS = EventBus()
