def available() -> bool:
    try:
        import edge_tts  # noqa: F401

        return True
    except Exception:
        return False
