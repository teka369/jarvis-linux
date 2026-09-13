from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

CACHE = Path.home() / ".cache" / "jarvis-linux"


class CameraError(RuntimeError):
    pass


@dataclass
class CameraDevice:
    path: str
    name: str


def list_cameras() -> list[CameraDevice]:
    devices: list[CameraDevice] = []
    video = Path("/dev")
    if not video.exists():
        return devices
    for node in sorted(video.glob("video*")):
        name = _sys_name(node) or node.name
        devices.append(CameraDevice(path=str(node), name=name))
    return devices


def probe() -> dict[str, object]:
    cams = list_cameras()
    return {
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "fswebcam": bool(shutil.which("fswebcam")),
        "devices": [{"path": c.path, "name": c.name} for c in cams],
    }


def capture_frame(dest: Path | None = None, device: str = "auto") -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = dest or (CACHE / "camera.jpg")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    candidates = _candidates(device)
    if not candidates:
        raise CameraError(
            "No hay nodos /dev/video*. Revisa que la webcam esté conectada y que "
            "tu usuario esté en el grupo video."
        )
    if not shutil.which("ffmpeg") and not shutil.which("fswebcam"):
        raise CameraError("Instala ffmpeg (recomendado) o fswebcam.")
    errors: list[str] = []
    for cam in candidates:
        err = _try_capture(cam.path, dest)
        if dest.exists() and dest.stat().st_size > 500:
            return dest
        errors.append(f"{cam.path} ({cam.name}): {err}")
    raise CameraError("No pude capturar un frame. " + " | ".join(errors))


def _candidates(device: str) -> list[CameraDevice]:
    all_cams = list_cameras()
    if device and device != "auto":
        return [c for c in all_cams if c.path == device] or [CameraDevice(device, device)]
    evens = [c for c in all_cams if _index(c.path) % 2 == 0]
    odds = [c for c in all_cams if _index(c.path) % 2 == 1]
    return evens + odds


def _index(path: str) -> int:
    digits = "".join(ch for ch in Path(path).name if ch.isdigit())
    return int(digits) if digits else 99


def _sys_name(node: Path) -> str:
    sysfs = Path("/sys/class/video4linux") / node.name / "name"
    if sysfs.exists():
        return sysfs.read_text(encoding="utf-8", errors="ignore").strip()
    return ""


def _try_capture(device: str, dest: Path) -> str:
    attempts: list[list[str]] = []
    if shutil.which("ffmpeg"):
        attempts.append(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "v4l2", "-input_format", "mjpeg", "-i", device, "-frames:v", "1", str(dest)]
        )
        attempts.append(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "v4l2", "-i", device, "-frames:v", "1", str(dest)]
        )
    if shutil.which("fswebcam"):
        attempts.append(["fswebcam", "-d", device, "-r", "1280x720", "--no-banner", str(dest)])
    last = "sin intentos"
    for cmd in attempts:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        if dest.exists() and dest.stat().st_size > 500:
            return "ok"
        last = (completed.stderr or completed.stdout or f"exit {completed.returncode}").strip()[:240]
    return last
