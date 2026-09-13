from __future__ import annotations

import json
import math
from pathlib import Path

from ..core.events import AvatarState, BUS
from .avatar.engine import AvatarEngine
from .qtboot import ensure_pyside

POS_FILE = Path.home() / ".config" / "jarvis-linux" / "avatar.json"
MIN_SIZE = 160
MAX_SIZE = 560


def load_geom() -> dict:
    if POS_FILE.exists():
        try:
            return json.loads(POS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"x": 80, "y": 80, "size": 320, "opacity": 0.97}


def save_geom(x: int, y: int, size: int, opacity: float) -> None:
    POS_FILE.parent.mkdir(parents=True, exist_ok=True)
    POS_FILE.write_text(json.dumps({"x": x, "y": y, "size": size, "opacity": opacity}), encoding="utf-8")


def run_overlay(on_listen, on_quit):
    if not ensure_pyside():
        print("Falta PySide6 visible para el venv.")
        print("CachyOS: sudo pacman -S pyside6 && ./install.sh")
        return 2
    from PySide6.QtCore import Qt, QTimer, QPoint
    from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QRadialGradient, QPainterPath
    from PySide6.QtWidgets import QApplication, QWidget, QMenu

    geom = load_geom()
    engine = AvatarEngine()

    class Core(QWidget):
        def __init__(self) -> None:
            flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
            super().__init__(None, flags)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, False)
            size = max(MIN_SIZE, min(MAX_SIZE, int(geom.get("size") or 320)))
            self.resize(size, size)
            self.move(int(geom.get("x") or 80), int(geom.get("y") or 80))
            self.setWindowOpacity(float(geom.get("opacity") or 0.97))
            self.setMouseTracking(True)
            self._drag: QPoint | None = None
            timer = QTimer(self)
            timer.timeout.connect(self._tick)
            timer.start(28)

        def _persist(self) -> None:
            save_geom(self.x(), self.y(), self.width(), self.windowOpacity())

        def _tick(self) -> None:
            if BUS.state == AvatarState.HIDDEN:
                if self.isVisible():
                    self.hide()
                return
            if not self.isVisible():
                self.show()
            idle = BUS.state == AvatarState.IDLE
            engine.tick(BUS.state, BUS.energy, 0.045 if idle else 0.028)
            self.update()

        def wheelEvent(self, event) -> None:
            step = 24 if event.angleDelta().y() > 0 else -24
            new = max(MIN_SIZE, min(MAX_SIZE, self.width() + step))
            if new == self.width():
                return
            cx = self.x() + self.width() // 2
            cy = self.y() + self.height() // 2
            self.resize(new, new)
            self.move(cx - new // 2, cy - new // 2)
            self._persist()

        def paintEvent(self, _event) -> None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            cx, cy = w / 2, h / 2
            scale = w / 320
            color = engine.palette(BUS.state)
            pulse = engine.pulse
            veil = QRadialGradient(cx, cy, w * 0.52)
            veil.setColorAt(0.0, QColor(6, 10, 28, int(90 + pulse * 40)))
            veil.setColorAt(0.55, QColor(4, 8, 22, 40))
            veil.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(veil))
            painter.drawEllipse(2, 2, w - 4, h - 4)
            for s in engine.stars:
                tw = 80 + int((math.sin(s.twinkle) + 1) * 70)
                painter.setBrush(QColor(190, 220, 255, tw))
                painter.drawEllipse(int(s.x * w), int(s.y * h), max(1, int(s.size)), max(1, int(s.size)))
            for arm in range(4):
                path = QPainterPath()
                for i in range(36):
                    t = i / 35
                    ang = engine.phase * 0.55 + arm * math.tau / 4 + t * 3.4
                    rad = (22 + t * 108) * scale * (1 + pulse * 0.12)
                    px = cx + math.cos(ang) * rad
                    py = cy + math.sin(ang) * rad * 0.72
                    if i == 0:
                        path.moveTo(px, py)
                    else:
                        path.lineTo(px, py)
                pen = QPen(QColor(color[0], color[1], color[2], 28 + arm * 10))
                pen.setWidthF(1.15 * scale)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)
            for i, (rx, ry, rot) in enumerate(((0.20, 0.11, 18), (0.29, 0.16, -27), (0.38, 0.20, 41))):
                painter.save()
                painter.translate(cx, cy)
                painter.rotate(rot + engine.phase * (8 + i * 6))
                pen = QPen(QColor(color[0], color[1], color[2], 55 + i * 18))
                pen.setWidthF(1.05)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                grow = 1 + pulse * 0.14
                painter.drawEllipse(int(-w * rx * grow), int(-h * ry * grow), int(w * rx * 2 * grow), int(h * ry * 2 * grow))
                painter.restore()
            painter.setPen(Qt.PenStyle.NoPen)
            for p in engine.particles:
                ang = p.angle + p.arm * 0.7
                rad = p.radius * scale * (1 + pulse * 0.08)
                x = cx + math.cos(ang) * rad
                y = cy + math.sin(ang) * rad * (0.58 + 0.18 * p.z)
                alpha = int((70 + pulse * 140) * p.z)
                painter.setBrush(QColor(color[0], color[1], min(255, color[2] + 20), min(255, alpha)))
                s = p.size * scale * (0.7 + pulse + p.z * 0.4)
                painter.drawEllipse(int(x), int(y), max(1, int(s)), max(1, int(s)))
            halo = QRadialGradient(cx, cy, w * 0.22 * (1 + pulse * 0.35))
            halo.setColorAt(0.0, QColor(255, 255, 255, 210))
            halo.setColorAt(0.18, QColor(color[0], color[1], color[2], 200))
            halo.setColorAt(0.45, QColor(color[0], 80, 220, 70))
            halo.setColorAt(1.0, QColor(color[0], color[1], color[2], 0))
            painter.setBrush(QBrush(halo))
            cr = w * 0.11 * (1 + pulse * 0.55)
            painter.drawEllipse(int(cx - cr), int(cy - cr), int(cr * 2), int(cr * 2))
            if BUS.state in {AvatarState.SPEAKING, AvatarState.LISTENING}:
                path = QPainterPath()
                segs = 64
                base = w * 0.16 * (1 + pulse * 0.25)
                for i in range(segs + 1):
                    ang = engine.phase * 1.7 + i / segs * math.tau
                    amp = base + math.sin(ang * 6 + engine.phase * 10) * (5 + BUS.energy * 18) * scale
                    px = cx + math.cos(ang) * amp
                    py = cy + math.sin(ang) * amp * 0.88
                    if i == 0:
                        path.moveTo(px, py)
                    else:
                        path.lineTo(px, py)
                pen = QPen(QColor(210, 240, 255, 190))
                pen.setWidthF(1.5)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)
            painter.end()

        def mousePressEvent(self, event) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.grabMouse()
            elif event.button() == Qt.MouseButton.RightButton:
                menu = QMenu(self)
                menu.addAction("Escuchar", on_listen)
                menu.addAction("Más grande", lambda: self._resize_by(32))
                menu.addAction("Más pequeño", lambda: self._resize_by(-32))
                menu.addAction("Ocultar", lambda: BUS.set_state(AvatarState.HIDDEN))
                menu.addAction("Salir", on_quit)
                menu.exec(event.globalPosition().toPoint())

        def _resize_by(self, step: int) -> None:
            new = max(MIN_SIZE, min(MAX_SIZE, self.width() + step))
            cx = self.x() + self.width() // 2
            cy = self.y() + self.height() // 2
            self.resize(new, new)
            self.move(cx - new // 2, cy - new // 2)
            self._persist()

        def mouseMoveEvent(self, event) -> None:
            if self._drag is not None and event.buttons() & Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag)

        def mouseReleaseEvent(self, _event) -> None:
            if self._drag is not None:
                self.releaseMouse()
            self._drag = None
            self._persist()

        def mouseDoubleClickEvent(self, _event) -> None:
            on_listen()

    app = QApplication.instance() or QApplication([])
    win = Core()
    win.show()
    BUS.set_state(AvatarState.IDLE)
    return app, win
