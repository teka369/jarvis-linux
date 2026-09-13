from __future__ import annotations

import json
import math
from pathlib import Path

from ..core.events import AvatarState, BUS
from .avatar.engine import AvatarEngine
from .qtboot import ensure_pyside

POS_FILE = Path.home() / ".config" / "jarvis-linux" / "avatar.json"


def load_geom() -> dict:
    if POS_FILE.exists():
        try:
            return json.loads(POS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"x": 60, "y": 80, "size": 280, "opacity": 0.92}


def save_geom(x: int, y: int, size: int, opacity: float) -> None:
    POS_FILE.parent.mkdir(parents=True, exist_ok=True)
    POS_FILE.write_text(json.dumps({"x": x, "y": y, "size": size, "opacity": opacity}), encoding="utf-8")


def run_overlay(on_listen, on_quit):
    if not ensure_pyside():
        print("Falta PySide6 visible para el venv.")
        print("CachyOS: sudo pacman -S pyside6 && ./install.sh")
        return 2
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QRadialGradient, QPainterPath
    from PySide6.QtWidgets import QApplication, QWidget, QMenu

    geom = load_geom()
    engine = AvatarEngine()

    class Core(QWidget):
        def __init__(self) -> None:
            super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
            size = int(geom.get("size") or 280)
            self.resize(size, size)
            self.move(int(geom.get("x") or 60), int(geom.get("y") or 80))
            self.setWindowOpacity(float(geom.get("opacity") or 0.92))
            self._drag = None
            timer = QTimer(self)
            timer.timeout.connect(self._tick)
            timer.start(33)

        def _tick(self) -> None:
            if BUS.state == AvatarState.HIDDEN:
                if self.isVisible():
                    self.hide()
                return
            if not self.isVisible():
                self.show()
            idle = BUS.state in {AvatarState.IDLE, AvatarState.HIDDEN}
            engine.tick(BUS.state, BUS.energy, 0.05 if idle else 0.033)
            self.update()

        def paintEvent(self, _event) -> None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            cx, cy = w / 2, h / 2
            color = engine.palette(BUS.state)
            pulse = engine.pulse
            glow = QRadialGradient(cx, cy, w * 0.48)
            glow.setColorAt(0.0, QColor(color[0], color[1], color[2], int(70 + pulse * 90)))
            glow.setColorAt(0.45, QColor(color[0], color[1], color[2], 28))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, w, h)
            for i, radius in enumerate((0.22, 0.31, 0.39)):
                pen = QPen(QColor(color[0], color[1], color[2], 50 + i * 20))
                pen.setWidthF(1.1)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                r = w * radius * (1 + pulse * 0.12)
                painter.save()
                painter.translate(cx, cy)
                painter.rotate(engine.phase * (12 + i * 18))
                painter.drawEllipse(int(-r), int(-r * 0.55), int(r * 2), int(r * 1.1))
                painter.restore()
            painter.setPen(Qt.PenStyle.NoPen)
            for p in engine.particles:
                x = cx + math.cos(p.angle) * p.radius * (w / 280)
                y = cy + math.sin(p.angle) * p.radius * 0.62 * (h / 280)
                painter.setBrush(QColor(color[0], color[1], color[2], min(255, 90 + int(pulse * 140))))
                s = p.size * (1 + pulse)
                painter.drawEllipse(int(x), int(y), int(s), int(s))
            core = QRadialGradient(cx, cy, w * 0.12 * (1 + pulse))
            core.setColorAt(0.0, QColor(255, 255, 255, 220))
            core.setColorAt(0.35, QColor(color[0], color[1], color[2], 200))
            core.setColorAt(1.0, QColor(color[0], color[1], color[2], 0))
            painter.setBrush(QBrush(core))
            cr = w * 0.09 * (1 + pulse * 0.5)
            painter.drawEllipse(int(cx - cr), int(cy - cr), int(cr * 2), int(cr * 2))
            if BUS.state in {AvatarState.SPEAKING, AvatarState.LISTENING}:
                path = QPainterPath()
                segs = 48
                rad = w * 0.18 * (1 + pulse * 0.3)
                for i in range(segs + 1):
                    ang = engine.phase * 2 + i / segs * math.tau
                    amp = rad + math.sin(ang * 5 + engine.phase * 8) * (6 + BUS.energy * 16)
                    px = cx + math.cos(ang) * amp
                    py = cy + math.sin(ang) * amp * 0.9
                    if i == 0:
                        path.moveTo(px, py)
                    else:
                        path.lineTo(px, py)
                pen = QPen(QColor(200, 240, 255, 160))
                pen.setWidthF(1.4)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)
            painter.end()

        def mousePressEvent(self, event) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            elif event.button() == Qt.MouseButton.RightButton:
                menu = QMenu(self)
                menu.addAction("Escuchar", on_listen)
                menu.addAction("Ocultar", lambda: BUS.set_state(AvatarState.HIDDEN))
                menu.addAction("Mostrar", lambda: BUS.set_state(AvatarState.IDLE))
                menu.addAction("Salir", on_quit)
                menu.exec(event.globalPosition().toPoint())

        def mouseMoveEvent(self, event) -> None:
            if self._drag is not None and event.buttons() & Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag)

        def mouseReleaseEvent(self, _event) -> None:
            self._drag = None
            save_geom(self.x(), self.y(), self.width(), self.windowOpacity())

        def mouseDoubleClickEvent(self, _event) -> None:
            on_listen()

    app = QApplication.instance() or QApplication([])
    win = Core()
    win.show()
    BUS.set_state(AvatarState.IDLE)
    return app, win
