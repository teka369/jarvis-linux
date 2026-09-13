from __future__ import annotations

import json
import math
from pathlib import Path

from ..core.events import AvatarState, BUS
from .avatar.engine import AvatarEngine
from .avatar.humanoid import HumanoidRig
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
    return {"x": 80, "y": 80, "size": 320, "opacity": 0.97, "style": "galaxy", "pin": True}


def save_geom(data: dict) -> None:
    POS_FILE.parent.mkdir(parents=True, exist_ok=True)
    POS_FILE.write_text(json.dumps(data), encoding="utf-8")


def run_overlay(on_listen, on_quit):
    if not ensure_pyside():
        print("Falta PySide6 visible para el venv.")
        return 2
    from PySide6.QtCore import Qt, QTimer, QPoint
    from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QRadialGradient, QPainterPath, QRegion
    from PySide6.QtWidgets import QApplication, QWidget, QMenu

    geom = load_geom()
    engine = AvatarEngine()

    class Core(QWidget):
        def __init__(self) -> None:
            flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window
            super().__init__(None, flags)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            size = max(MIN_SIZE, min(MAX_SIZE, int(geom.get("size") or 320)))
            self.setMinimumSize(size, size)
            self.setMaximumSize(size, size)
            self.resize(size, size)
            self.move(int(geom.get("x") or 80), int(geom.get("y") or 80))
            self.setWindowOpacity(float(geom.get("opacity") or 0.97))
            self.setMouseTracking(True)
            self._drag: QPoint | None = None
            self._style = str(geom.get("style") or "galaxy")
            self._pin = bool(geom.get("pin", True))
            self._rig = HumanoidRig()
            timer = QTimer(self)
            timer.timeout.connect(self._tick)
            timer.start(28)
            self._apply_pin()

        def _persist(self) -> None:
            save_geom({"x": self.x(), "y": self.y(), "size": self.width(), "opacity": self.windowOpacity(), "style": self._style, "pin": self._pin})

        def _tick(self) -> None:
            if BUS.state == AvatarState.HIDDEN:
                self.hide()
                return
            if not self.isVisible():
                self.show()
            dt = 0.045 if BUS.state == AvatarState.IDLE else 0.028
            engine.tick(BUS.state, BUS.energy, dt)
            self._rig.tick(BUS.state, BUS.energy, dt)
            self.update()

        def _apply_size(self, new: int) -> None:
            new = max(MIN_SIZE, min(MAX_SIZE, int(new)))
            cx, cy = self.x() + self.width() // 2, self.y() + self.height() // 2
            self.setMinimumSize(new, new)
            self.setMaximumSize(new, new)
            self.resize(new, new)
            self.move(max(0, cx - new // 2), max(0, cy - new // 2))
            self._persist()

        def wheelEvent(self, event) -> None:
            self._apply_size(self.width() + (28 if event.angleDelta().y() > 0 else -28))

        def resizeEvent(self, event) -> None:
            if self._style == "humanoid":
                self.clearMask()
            else:
                self.setMask(QRegion(0, 0, self.width(), self.height(), QRegion.RegionType.Ellipse))
            super().resizeEvent(event)

        def _set_style(self, style: str) -> None:
            self._style = style
            if style == "humanoid":
                self.clearMask()
            else:
                self.setMask(QRegion(0, 0, self.width(), self.height(), QRegion.RegionType.Ellipse))
            self._persist()
            self.update()

        def _toggle_pin(self) -> None:
            self._pin = not self._pin
            self._apply_pin()
            self._persist()

        def _apply_pin(self) -> None:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            self.setWindowFlag(Qt.WindowType.Tool, self._pin)
            self.show()

        def paintEvent(self, _event) -> None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            painter.fillRect(0, 0, w, h, QColor(2, 4, 12, 18))
            if self._style == "humanoid":
                self._paint_humanoid(painter, w, h)
                painter.end()
                return
            cx, cy = w / 2, h / 2
            scale = w / 320
            color = engine.palette(BUS.state)
            pulse = engine.pulse
            veil = QRadialGradient(cx, cy, w * 0.52)
            veil.setColorAt(0.0, QColor(6, 10, 28, int(90 + pulse * 40)))
            veil.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(veil))
            painter.drawEllipse(2, 2, w - 4, h - 4)
            for s in engine.stars:
                painter.setBrush(QColor(190, 220, 255, 120))
                painter.drawEllipse(int(s.x * w), int(s.y * h), 2, 2)
            for p in engine.particles:
                ang = p.angle + p.arm * 0.7
                rad = p.radius * scale
                painter.setBrush(QColor(color[0], color[1], color[2], 140))
                painter.drawEllipse(int(cx + math.cos(ang) * rad), int(cy + math.sin(ang) * rad * 0.62), 2, 2)
            halo = QRadialGradient(cx, cy, w * 0.2)
            halo.setColorAt(0.0, QColor(255, 255, 255, 210))
            halo.setColorAt(1.0, QColor(color[0], color[1], color[2], 0))
            painter.setBrush(QBrush(halo))
            cr = w * 0.11
            painter.drawEllipse(int(cx - cr), int(cy - cr), int(cr * 2), int(cr * 2))
            painter.end()

        def _paint_humanoid(self, painter, w: int, h: int) -> None:
            color = engine.palette(BUS.state)
            pose = self._rig.pose(BUS.state, BUS.energy)
            pulse = engine.pulse

            def xy(key):
                j = pose[key]
                return int(j.x * w), int(j.y * h)

            def bone(a, b, width=3.0):
                pen = QPen(QColor(color[0], color[1], color[2], 200))
                pen.setWidthF(width)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                x1, y1 = xy(a)
                x2, y2 = xy(b)
                painter.drawLine(x1, y1, x2, y2)

            for a, b in (("l_ft", "l_kn"), ("l_kn", "l_hip"), ("r_ft", "r_kn"), ("r_kn", "r_hip"), ("l_hip", "r_hip"), ("hip", "chest"), ("chest", "neck"), ("neck", "head"), ("chest", "l_sh"), ("chest", "r_sh"), ("l_sh", "l_el"), ("l_el", "l_h"), ("r_sh", "r_el"), ("r_el", "r_h")):
                bone(a, b)
            hx, hy = xy("head")
            hr = int(w * 0.078)
            painter.setBrush(QColor(color[0], color[1], color[2], 160))
            painter.setPen(QPen(QColor(200, 230, 255, 180), 1.3))
            painter.drawEllipse(hx - hr, hy - hr, hr * 2, hr * 2)
            painter.setBrush(QColor(230, 250, 255, 230))
            painter.setPen(Qt.PenStyle.NoPen)
            eh = max(1, int(hr * 0.16 * self._rig.blink))
            painter.drawEllipse(hx - int(hr * 0.32) - 2, hy - eh, 4, eh * 2)
            painter.drawEllipse(hx + int(hr * 0.32) - 2, hy - eh, 4, eh * 2)
            mh = max(1, int(hr * 0.16 * self._rig.mouth(BUS.state, BUS.energy)))
            painter.drawRoundedRect(hx - 8, hy + int(hr * 0.28), 16, mh, 3, 3)
            cx, cy = xy("chest")
            painter.setBrush(QColor(255, 255, 255, 180))
            painter.drawEllipse(cx - 6, cy - 6, 12, 12)

        def mousePressEvent(self, event) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                handle = self.windowHandle()
                if handle is not None and handle.startSystemMove():
                    return
                self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            elif event.button() == Qt.MouseButton.RightButton:
                menu = QMenu(self)
                menu.addAction("Escuchar", on_listen)
                menu.addAction("Avatar galaxia", lambda: self._set_style("galaxy"))
                menu.addAction("Avatar humanoide", lambda: self._set_style("humanoid"))
                menu.addAction("Quitar persistente" if self._pin else "Fijar en todos los escritorios", self._toggle_pin)
                menu.addAction("Más grande", lambda: self._resize_by(32))
                menu.addAction("Más pequeño", lambda: self._resize_by(-32))
                menu.addAction("Ocultar", lambda: BUS.set_state(AvatarState.HIDDEN))
                menu.addAction("Salir", on_quit)
                menu.exec(event.globalPosition().toPoint())

        def _resize_by(self, step: int) -> None:
            self._apply_size(self.width() + step)

        def mouseMoveEvent(self, event) -> None:
            if self._drag is not None and event.buttons() & Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag)

        def mouseReleaseEvent(self, _event) -> None:
            self._drag = None
            self._persist()

        def mouseDoubleClickEvent(self, _event) -> None:
            on_listen()

    app = QApplication.instance() or QApplication([])
    win = Core()
    win.show()
    BUS.set_state(AvatarState.IDLE)
    return app, win
