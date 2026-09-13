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
    rate = settings.sample_rate
    block = int(rate * 0.02)
    max_seconds = 6.5 if primed else min(settings.max_utterance_seconds, 8.0)
    max_frames = int(rate * max_seconds)
    silence_needed = max(8, int(0.45 / 0.02))
    started = primed
    silent_blocks = 0
    voiced = 0
    chunks: list[np.ndarray] = []
    frames = 0
    peak = 0.0
    noise_samples: list[float] = []
    deadline = time.time() + max_seconds + 0.8

    with sd.InputStream(samplerate=rate, channels=1, dtype="float32", blocksize=block) as stream:
        while time.time() < deadline and frames < max_frames:
            data, _ = stream.read(block)
            mono = np.squeeze(data).astype(np.float32, copy=False)
            energy = _rms(mono)
            if len(noise_samples) < 12:
                noise_samples.append(energy)
            noise = float(np.median(noise_samples)) if noise_samples else 0.004
            gate = max(settings.energy_threshold, noise * 3.2 + 0.01)
            if energy > peak:
                peak = energy
            if not started:
                if energy >= gate:
                    started = True
                    chunks.append(mono.copy())
                    frames += mono.size
                    voiced += 1
                continue
            chunks.append(mono.copy())
            frames += mono.size
            talking = energy >= max(gate, peak * 0.22)
            if talking:
                voiced += 1
                silent_blocks = 0
            else:
                silent_blocks += 1
                if voiced >= 6 and silent_blocks >= silence_needed:
                    break
                if primed and voiced == 0 and frames > rate * 1.2 and silent_blocks >= silence_needed:
                    break

    dest.parent.mkdir(parents=True, exist_ok=True)
    audio = np.concatenate(chunks) if chunks else np.zeros(rate // 5, dtype=np.float32)
    pcm = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(dest), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())
    return dest
