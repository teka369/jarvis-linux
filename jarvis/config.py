from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
HOME_CFG = Path.home() / ".config" / "jarvis-linux"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class Settings:
    name: str = "Jarvis"
    language: str = "es"
    wake_words: list[str] = field(default_factory=lambda: ["jarvis"])
    personality: str = "Eres J.A.R.V.I.S."
    sample_rate: int = 16000
    channels: int = 1
    max_utterance_seconds: float = 12.0
    silence_seconds: float = 1.1
    energy_threshold: float = 0.012
    hotkey_enabled: bool = True
    hotkey: str = "<cmd>+j"
    tts_voice: str = "es-CO-GonzaloNeural"
    tts_rate: str = "+8%"
    tts_volume: str = "+0%"
    stt_order: list[str] = field(default_factory=lambda: ["groq", "gemini"])
    llm_order: list[str] = field(default_factory=lambda: ["gemini", "groq"])
    vision_order: list[str] = field(default_factory=lambda: ["gemini"])
    groq_stt_model: str = "whisper-large-v3-turbo"
    groq_llm_model: str = "openai/gpt-oss-120b"
    gemini_llm_model: str = "gemini-2.5-flash"
    gemini_vision_model: str = "gemini-2.5-flash"
    nvidia_llm_model: str = "z-ai/glm-5.3-flash"
    openrouter_llm_model: str = "openrouter/auto"
    allow_shell: bool = True
    allowed_bins: list[str] = field(default_factory=list)
    forbidden_patterns: list[str] = field(default_factory=list)
    default_browser: str = "firefox"
    terminal: str = "konsole"
    notes_dir: str = "~/Documents/jarvis"
    groq_api_key: str = ""
    gemini_api_key: str = ""
    nvidia_api_key: str = ""
    openrouter_api_key: str = ""
    xai_api_key: str = ""

    @property
    def notes_path(self) -> Path:
        return Path(self.notes_dir).expanduser()


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    load_dotenv(HOME_CFG / ".env")

    raw = _load_yaml(ROOT / "config.example.yaml")
    raw = _deep_merge(raw, _load_yaml(ROOT / "config.yaml"))
    raw = _deep_merge(raw, _load_yaml(HOME_CFG / "config.yaml"))

    assistant = raw.get("assistant") or {}
    audio = raw.get("audio") or {}
    hotkey = raw.get("hotkey") or {}
    tts = raw.get("tts") or {}
    providers = raw.get("providers") or {}
    safety = raw.get("safety") or {}
    desktop = raw.get("desktop") or {}

    return Settings(
        name=assistant.get("name", "Jarvis"),
        language=assistant.get("language", "es"),
        wake_words=[w.lower() for w in assistant.get("wake_words", ["jarvis"])],
        personality=(assistant.get("personality") or "Eres J.A.R.V.I.S.").strip(),
        sample_rate=int(audio.get("sample_rate", 16000)),
        channels=int(audio.get("channels", 1)),
        max_utterance_seconds=float(audio.get("max_utterance_seconds", 12)),
        silence_seconds=float(audio.get("silence_seconds", 1.1)),
        energy_threshold=float(audio.get("energy_threshold", 0.012)),
        hotkey_enabled=bool(hotkey.get("enabled", True)),
        hotkey=str(hotkey.get("combination", "<cmd>+j")),
        tts_voice=str(tts.get("voice", "es-CO-GonzaloNeural")),
        tts_rate=str(tts.get("rate", "+8%")),
        tts_volume=str(tts.get("volume", "+0%")),
        stt_order=list(providers.get("stt_order") or ["groq", "gemini"]),
        llm_order=list(providers.get("llm_order") or ["gemini", "groq"]),
        vision_order=list(providers.get("vision_order") or ["gemini"]),
        groq_stt_model=str(providers.get("groq_stt_model", "whisper-large-v3-turbo")),
        groq_llm_model=str(providers.get("groq_llm_model", "openai/gpt-oss-120b")),
        gemini_llm_model=str(providers.get("gemini_llm_model", "gemini-2.5-flash")),
        gemini_vision_model=str(providers.get("gemini_vision_model", "gemini-2.5-flash")),
        nvidia_llm_model=str(providers.get("nvidia_llm_model", "z-ai/glm-5.3-flash")),
        openrouter_llm_model=str(providers.get("openrouter_llm_model", "openrouter/auto")),
        allow_shell=bool(safety.get("allow_shell", True)),
        allowed_bins=list(safety.get("allowed_bins") or []),
        forbidden_patterns=list(safety.get("forbidden_patterns") or []),
        default_browser=str(desktop.get("default_browser", "firefox")),
        terminal=str(desktop.get("terminal", "konsole")),
        notes_dir=str(desktop.get("notes_dir", "~/Documents/jarvis")),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        nvidia_api_key=os.getenv("NVIDIA_API_KEY", ""),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        xai_api_key=os.getenv("XAI_API_KEY", ""),
    )


def _deep_merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out
