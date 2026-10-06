"""La boule de Jarvis : un réacteur animé qui flotte sur l'écran (style Iron Man).

- Glisser avec la souris pour la déplacer (la position est mémorisée).
- Clic : Jarvis t'écoute sans que tu dises « Jarvis ».
- Double-clic : ouvre l'interface complète.
- Clic droit : position (derrière les fenêtres, normale, premier plan), masquer, quitter.
- Ctrl+Alt+J (partout dans Windows) : afficher / masquer.
"""

from __future__ import annotations

import math
import random
import time
import webbrowser

from . import config, state

SIZE = 240          # diamètre de la zone de la boule
CAPTION_H = 70      # hauteur de la zone de sous-titres
HOTKEY = "<ctrl>+<alt>+j"

COLORS = {
    state.IDLE: (79, 214, 255),
    state.LISTENING: (255, 181, 71),
    state.THINKING: (79, 214, 255),
    state.SPEAKING: (120, 230, 255),
}
SPEEDS = {state.IDLE: 1.0, state.LISTENING: 1.6, state.THINKING: 4.5, state.SPEAKING: 1.8}


def available() -> bool:
    try:
        import PySide6  # noqa: F401
    except ImportError:
        return False
    return True


def run(on_quit=None) -> None:
    """Affiche la boule ; bloque jusqu'à sa fermeture (à appeler dans le fil principal)."""
    from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
    from PySide6.QtGui import (QAction, QBrush, QColor, QFont, QPainter, QPainterPath, QPen,
                               QRadialGradient)
    from PySide6.QtWidgets import QApplication, QMenu, QWidget

    class Orb(QWidget):
        def __init__(self) -> None:
            super().__init__()
            # Où se place la boule : « derriere » (sur le bureau, sous les fenêtres), « normal »
            # (comme une fenêtre classique) ou « devant » (toujours au premier plan).
            legacy = "devant" if config.load().get("orbe_premier_plan") == "oui" else "derriere"
            self.layer = config.get("orbe_plan") or legacy
            self.last_lower = 0.0
            self._apply_flags()
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setWindowTitle("Jarvis")
            self.resize(SIZE + 120, SIZE + CAPTION_H)
            self._restore_position()
            self.angle = 0.0
            self.level = 0.0
            self.color = QColor(*COLORS[state.IDLE])
            self.drag_from = None
            self.moved = False
            self.last = time.monotonic()
            self.timer = QTimer(self, timeout=self.tick)
            self.timer.start(16)  # ~60 images par seconde

        # --- fenêtre ---------------------------------------------------------

        def _apply_flags(self) -> None:
            flags = Qt.FramelessWindowHint | Qt.Tool
            if self.layer == "devant":
                flags |= Qt.WindowStaysOnTopHint
            elif self.layer == "derriere":
                flags |= Qt.WindowStaysOnBottomHint
            self.setWindowFlags(flags)

        def _restore_position(self) -> None:
            screen = QApplication.primaryScreen().availableGeometry()
            try:
                x, y = (int(v) for v in (config.get("orbe_position") or "").split(","))
            except ValueError:
                x, y = screen.right() - self.width() - 20, screen.bottom() - self.height() - 20
            self.move(x, y)

        def set_layer(self, layer: str) -> None:
            self.layer = layer
            config.save("orbe_plan", layer)
            visible = self.isVisible()
            self._apply_flags()
            if visible:
                self.show()
                if layer == "derriere":
                    self.lower()

        def toggle_visible(self) -> None:
            self.hide() if self.isVisible() else (self.show(), self.raise_())

        # --- animation -------------------------------------------------------

        def tick(self) -> None:
            action = state.take_visibility_request()
            if action == "masquer":
                self.hide()
            elif action == "afficher":
                self.show()
                self.raise_()
            elif action == "basculer":
                self.toggle_visible()

            now = time.monotonic()
            dt, self.last = now - self.last, now
            if self.layer == "derriere" and now - self.last_lower > 2 and self.drag_from is None:
                self.lower()  # reste sous les fenêtres, même après un clic
                self.last_lower = now
            current, _, _ = state.get()
            self.angle = (self.angle + dt * 30 * SPEEDS.get(current, 1.0)) % 360
            # Pulsation de la voix (le son lui-même n'est pas analysé) ou respiration au repos.
            if current == state.SPEAKING:
                target = 0.45 + 0.55 * abs(math.sin(now * 9)) * random.uniform(0.6, 1.0)
            elif current == state.THINKING:
                target = 0.35 + 0.25 * math.sin(now * 6)
            else:
                target = 0.15 + 0.1 * math.sin(now * 1.5)
            self.level += (target - self.level) * min(1.0, dt * 12)
            goal = QColor(*COLORS.get(current, COLORS[state.IDLE]))
            mix = min(1.0, dt * 6)
            self.color = QColor(
                int(self.color.red() + (goal.red() - self.color.red()) * mix),
                int(self.color.green() + (goal.green() - self.color.green()) * mix),
                int(self.color.blue() + (goal.blue() - self.color.blue()) * mix),
            )
            self.update()

        def _c(self, alpha: int) -> QColor:
            c = QColor(self.color)
            c.setAlpha(max(0, min(255, alpha)))
            return c

        def paintEvent(self, _event) -> None:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            cx, cy = self.width() / 2, SIZE / 2
            center = QPointF(cx, cy)
            r = SIZE / 2 - 8

            # Halo
            halo = QRadialGradient(center, r)
            halo.setColorAt(0.0, self._c(int(70 + 90 * self.level)))
            halo.setColorAt(0.45, self._c(int(25 + 40 * self.level)))
            halo.setColorAt(1.0, self._c(0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(halo))
            p.drawEllipse(center, r, r)

            # Disque sombre derrière les anneaux (lisibilité sur fond clair)
            p.setBrush(QColor(3, 10, 18, 225))
            p.drawEllipse(center, r * 0.86, r * 0.86)

            def arc(radius: float, start: float, span: float, width: float, alpha: int) -> None:
                pen = QPen(self._c(alpha), width)
                pen.setCapStyle(Qt.FlatCap)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
                p.drawArc(rect, int(start * 16), int(span * 16))

            # Graduations extérieures
            p.save()
            p.translate(center)
            p.rotate(-self.angle * 0.3)
            for i in range(72):
                p.setPen(QPen(self._c(200 if i % 6 == 0 else 90), 2 if i % 6 == 0 else 1))
                inner = r * (0.80 if i % 6 == 0 else 0.83)
                p.drawLine(QPointF(0, -inner), QPointF(0, -r * 0.86))
                p.rotate(5)
            p.restore()

            # Anneau segmenté (tourne dans un sens)
            for i in range(8):
                arc(r * 0.70, self.angle + i * 45, 32, 7, 150)
            # Anneau fin en pointillés (sens inverse)
            for i in range(24):
                arc(r * 0.60, -self.angle * 1.4 + i * 15, 8, 2, 200)
            # Arcs longs (rapides)
            arc(r * 0.52, self.angle * 2.2, 110, 3, 230)
            arc(r * 0.52, self.angle * 2.2 + 180, 60, 3, 230)

            # Cœur lumineux
            core_r = r * (0.24 + 0.12 * self.level)
            core = QRadialGradient(center, core_r * 1.8)
            core.setColorAt(0.0, QColor(240, 252, 255, 255))
            core.setColorAt(0.35, self._c(255))
            core.setColorAt(1.0, self._c(0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(core))
            p.drawEllipse(center, core_r * 1.8, core_r * 1.8)

            # Triangle du réacteur
            p.setPen(QPen(self._c(220), 2))
            p.setBrush(Qt.NoBrush)
            tri = QPainterPath()
            for k in range(4):
                a = math.radians(-90 + k * 120)
                pt = QPointF(cx + math.cos(a) * r * 0.40, cy + math.sin(a) * r * 0.40)
                tri.moveTo(pt) if k == 0 else tri.lineTo(pt)
            p.drawPath(tri)

            # Sous-titre : la dernière phrase, qui s'efface après quelques secondes
            current, caption, age = state.get()
            label = caption if caption and age < 8 else ""
            status = current.upper()
            p.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
            pill = QRectF(cx - 80, SIZE - 6, 160, 18)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(3, 10, 18, 200))
            p.drawRoundedRect(pill, 9, 9)
            p.setPen(self._c(240))
            p.drawText(pill, Qt.AlignCenter, f"J.A.R.V.I.S · {status}")
            if label:
                fade = 255 if age < 6 else int(255 * (8 - age) / 2)
                box = QRectF(6, SIZE + 14, self.width() - 12, CAPTION_H - 18)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(4, 12, 20, int(190 * fade / 255)))
                p.drawRoundedRect(box, 8, 8)
                p.setPen(QColor(220, 240, 250, fade))
                p.setFont(QFont("Segoe UI", 9))
                p.drawText(box.adjusted(8, 4, -8, -4), Qt.AlignCenter | Qt.TextWordWrap, label)
            p.end()

        # --- souris ----------------------------------------------------------

        def mousePressEvent(self, event) -> None:
            if event.button() == Qt.LeftButton:
                self.drag_from = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.moved = False

        def mouseMoveEvent(self, event) -> None:
            if self.drag_from is not None and event.buttons() & Qt.LeftButton:
                self.move(event.globalPosition().toPoint() - self.drag_from)
                self.moved = True

        def mouseReleaseEvent(self, event) -> None:
            if event.button() == Qt.LeftButton:
                if self.moved:
                    config.save("orbe_position", f"{self.x()},{self.y()}")
                else:
                    state.wake()  # clic simple : « je t'écoute »
                self.drag_from = None

        def mouseDoubleClickEvent(self, _event=None) -> None:
            self.open_interface()

        def open_interface(self) -> None:
            from .webui import PORT

            webbrowser.open(f"http://localhost:{PORT}")

        def contextMenuEvent(self, event) -> None:
            menu = QMenu(self)
            place = menu.addMenu("Position")
            for layer, label in (("derriere", "Derrière les fenêtres (sur le bureau)"),
                                 ("normal", "Comme une fenêtre normale"),
                                 ("devant", "Toujours au premier plan")):
                action = QAction(label, place, checkable=True, checked=self.layer == layer)
                action.triggered.connect(lambda *_, l=layer: self.set_layer(l))
                place.addAction(action)
            from . import startup_music

            if startup_music.is_playing():
                menu.addAction("Couper la musique", lambda *_: startup_music.stop())
            menu.addAction("Masquer (Ctrl+Alt+J pour revenir)", lambda *_: self.hide())
            menu.addAction("Ouvrir l'interface complète", lambda *_: self.open_interface())
            menu.addSeparator()
            menu.addAction("Quitter Jarvis", lambda *_: QApplication.quit())
            menu.exec(event.globalPos())

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    orb = Orb()
    if (config.get("orbe_visible", "oui") or "oui") != "non":
        orb.show()
    _start_hotkey()
    app.exec()
    if on_quit:
        on_quit()


def save_icon(path) -> None:
    """Dessine le réacteur en icône (pour le raccourci du Bureau)."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap, QRadialGradient

    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841 (nécessaire pour dessiner)
    size = 256
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    c = QPointF(size / 2, size / 2)
    cyan = QColor(79, 214, 255)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(3, 10, 18))
    p.drawEllipse(c, 124, 124)
    p.setPen(QPen(cyan, 14))
    for i in range(8):
        p.drawArc(26, 26, 204, 204, int((i * 45 + 6) * 16), int(32 * 16))
    p.setPen(QPen(cyan, 4))
    p.drawEllipse(c, 74, 74)
    glow = QRadialGradient(c, 64)
    glow.setColorAt(0, QColor(240, 252, 255))
    glow.setColorAt(0.4, cyan)
    glow.setColorAt(1, QColor(79, 214, 255, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(glow)
    p.drawEllipse(c, 64, 64)
    p.end()
    if not pix.save(str(path)):
        raise OSError(f"impossible d'écrire {path}")


def _start_hotkey() -> None:
    """Raccourci clavier global pour afficher / masquer la boule."""
    try:
        from pynput import keyboard

        listener = keyboard.GlobalHotKeys({HOTKEY: lambda: state.request_visibility("basculer")})
        listener.daemon = True
        listener.start()
    except Exception as exc:
        print(f"[boule] raccourci {HOTKEY} indisponible : {exc}")
