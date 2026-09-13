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
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = np.ascontiguousarray(audio, dtype=np.float32)
        hop = max(512, rate // 40)
        idx = {"n": 0}

        def callback(outdata, frames, _time, status):
            start = idx["n"]
            end = start + frames
            chunk = audio[start:end]
            if len(chunk) < frames:
                out = np.zeros((frames, 1), dtype=np.float32)
                if len(chunk):
                    out[: len(chunk), 0] = chunk
                    rms = float(np.sqrt(np.mean(chunk * chunk)))
                    BUS.set_energy(min(1.0, rms * 4.2))
                else:
                    BUS.set_energy(0.0)
                outdata[:] = out
                raise sd.CallbackStop()
            outdata[:, 0] = chunk
            rms = float(np.sqrt(np.mean(chunk * chunk)))
            BUS.set_energy(min(1.0, rms * 4.2))
            idx["n"] = end

        with sd.OutputStream(
            samplerate=rate,
            channels=1,
            dtype="float32",
            blocksize=hop,
            callback=callback,
        ):
            sd.sleep(int(len(audio) / rate * 1000) + 80)
        BUS.set_energy(0.0)
    finally:
        path.unlink(missing_ok=True)
