from __future__ import annotations

import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from ..config import Settings


def _rms(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(frame), dtype=np.float64)))


def record_utterance(settings: Settings, dest: Path, primed: bool = False) -> Path:
    """Graba hasta silencio o hasta el máximo de segundos."""
    rate = settings.sample_rate
    block = int(rate * 0.03)
    max_frames = int(rate * settings.max_utterance_seconds)
    silence_needed = int(settings.silence_seconds / 0.03)
    started = primed
    silent_blocks = 0
    chunks: list[np.ndarray] = []
    frames = 0
    deadline = time.time() + settings.max_utterance_seconds + 4

    with sd.InputStream(samplerate=rate, channels=1, dtype="float32", blocksize=block) as stream:
        while time.time() < deadline and frames < max_frames:
            data, _ = stream.read(block)
            mono = np.squeeze(data).astype(np.float32, copy=False)
            energy = _rms(mono)
            if not started:
                if energy >= settings.energy_threshold:
                    started = True
                    chunks.append(mono.copy())
                    frames += mono.size
                continue
            chunks.append(mono.copy())
            frames += mono.size
            if energy < settings.energy_threshold:
                silent_blocks += 1
                if silent_blocks >= silence_needed and frames > rate * 0.35:
                    break
            else:
                silent_blocks = 0

    dest.parent.mkdir(parents=True, exist_ok=True)
    audio = np.concatenate(chunks) if chunks else np.zeros(rate // 4, dtype=np.float32)
    pcm = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(dest), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    return dest
