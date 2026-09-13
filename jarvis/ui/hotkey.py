from __future__ import annotations

import select
import threading
from typing import Callable


def start_ptt_watch(on_down: Callable[[], None], on_up: Callable[[], None]) -> bool:
    try:
        from evdev import InputDevice, ecodes, list_devices
    except ImportError:
        return False
    devices = []
    for path in list_devices():
        try:
            devices.append(InputDevice(path))
        except OSError:
            continue
    if not devices:
        return False
    keys = {"meta": False, "shift": False, "j": False, "held": False}

    def loop() -> None:
        while True:
            try:
                readable, _, _ = select.select(devices, [], [], 0.4)
            except (OSError, ValueError):
                return
            for dev in readable:
                try:
                    events = list(dev.read())
                except OSError:
                    continue
                for ev in events:
                    if ev.type != ecodes.EV_KEY:
                        continue
                    pressed = ev.value != 0
                    if ev.code in (ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA):
                        keys["meta"] = pressed
                    elif ev.code in (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT):
                        keys["shift"] = pressed
                    elif ev.code == ecodes.KEY_J:
                        keys["j"] = pressed
                    combo = keys["meta"] and keys["shift"] and keys["j"]
                    if combo and not keys["held"]:
                        keys["held"] = True
                        on_down()
                    elif keys["held"] and not combo:
                        keys["held"] = False
                        on_up()

    threading.Thread(target=loop, daemon=True).start()
    return True
