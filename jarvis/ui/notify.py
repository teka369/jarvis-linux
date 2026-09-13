from __future__ import annotations

import shutil
import subprocess


def toast(title: str, body: str) -> None:
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "-a", "Jarvis", title, body], check=False)
    print(f"[{title}] {body}")
