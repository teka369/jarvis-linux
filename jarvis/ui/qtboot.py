from __future__ import annotations

import sys
from pathlib import Path


def ensure_pyside() -> bool:
    try:
        import PySide6  # noqa: F401
        return True
    except ImportError:
        pass
    roots = list(Path("/usr/lib").glob("python3*/site-packages"))
    roots += list(Path("/usr/lib64").glob("python3*/site-packages"))
    for root in roots:
        if (root / "PySide6").is_dir():
            path = str(root)
            if path not in sys.path:
                sys.path.insert(0, path)
            try:
                import PySide6  # noqa: F401
                return True
            except ImportError:
                continue
    return False
