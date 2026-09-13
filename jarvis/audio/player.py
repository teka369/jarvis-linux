from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import edge_tts
import numpy as np
import sounddevice as sd
import soundfile as sf

from ..config import Settings
from ..core.events import BUS


async def _synthesize(text: str, settings: Settings, dest: Path) -> None:
    communicate = edge_tts.Communicate(
        text=text, voice=settings.tts_voice, rate=settings.tts_rate, volume=settings.tts_volume
    )
    await communicate.save(str(dest))


def speak(text: str, settings: Settings) -> None:
    cleaned = " ".join(text.split())
    if not cleaned:
        return
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        asyncio.run(_synthesize(cleaned, settings, path))
        audio, rate = sf.read(path, dtype="float32")
        mono = audio.mean(axis=1) if audio.ndim > 1 else audio
        hop = max(1024, rate // 20)
        for start in range(0, len(mono), hop):
            chunk = mono[start : start + hop]
            rms = float(np.sqrt(np.mean(chunk * chunk))) if len(chunk) else 0.0
            BUS.set_energy(min(1.0, rms * 4.5))
            sd.play(chunk, rate)
            sd.wait()
        BUS.set_energy(0.0)
    finally:
        path.unlink(missing_ok=True)
