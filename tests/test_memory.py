from pathlib import Path

from jarvis.core.memory import Memory


def test_remember_recall_forget(tmp_path: Path):
    mem = Memory(tmp_path / "memory.json")
    assert "vacía" in mem.recall().lower() or "vacia" in mem.recall().lower()
    mem.remember("proyecto", "R.E.C")
    assert "R.E.C" in mem.recall("proyecto")
    assert "proyecto" in mem.context_block()
    mem.forget("proyecto")
    assert "nada" in mem.recall("proyecto").lower()
