from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import edge_tts
import sounddevice as sd
import soundfile as sf

from ..config import Settings


async def _synthesize(text: str, settings: Settings, dest: Path) -> None:
    communicate = edge_tts.Communicate(
        text=text,
        voice=settings.tts_voice,
        rate=settings.tts_rate,
        volume=settings.tts_volume,
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
        sd.play(audio, rate)
        sd.wait()
    finally:
        path.unlink(missing_ok=True)
