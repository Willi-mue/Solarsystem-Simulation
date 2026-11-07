"""Hauptfenster: verbindet Timer, Eingaben, Simulation und Renderer."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from importlib.resources import files

from PyQt5.QtCore import QPoint, Qt, QTimer
from PyQt5.QtGui import QIcon, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QWheelEvent
from PyQt5.QtWidgets import QApplication, QWidget

from . import config
from .bodies import create_asteroids, create_solar_system
from .camera import Camera
from .i18n import Translator
from .orbits import julian_date
from .physics import Simulation
from .playback import Playback
from .renderer import Renderer, Scene
from .trails import Trails

ICON_PATH = files("solarsystem") / "assets" / "icon.png"

TOGGLES = {
    Qt.Key_T: "show_trails",
    Qt.Key_O: "show_orbits",
    Qt.Key_L: "show_labels",
    Qt.Key_H: "show_help",
    Qt.Key_A: "show_asteroids",
}


class MainWindow(QWidget):
    def __init__(self, start_jd: float | None = None) -> None:
        """`start_jd`: Startdatum als Julianisches Datum (Standard: jetzt)."""
        super().__init__()
        self.translator = Translator(config.DEFAULT_LANGUAGE)
        self.setWindowTitle(self.translator.t("window_title"))
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setMinimumSize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        # Wunschgröße, aber nie größer als der verfügbare Bildschirm
        available = QApplication.primaryScreen().availableGeometry()
        self.resize(
            min(config.WINDOW_WIDTH, available.width()),
            min(config.WINDOW_HEIGHT, available.height()),
        )

        jd = start_jd if start_jd is not None else julian_date(datetime.now(timezone.utc))
        bodies = create_solar_system(jd)
        self.simulation = Simulation(bodies, create_asteroids(bodies[0]), start_jd=jd)
        self.scene = Scene(
            simulation=self.simulation,
            camera=Camera(),
            trails=Trails(bodies),
            playback=Playback(),
            translator=self.translator,
        )
        self.renderer = Renderer()

        self._press_pos: QPoint | None = None
        self._last_drag_pos: QPoint | None = None
        self._dragging = False
        self.setCursor(Qt.OpenHandCursor)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(config.FRAME_INTERVAL_MS)

    # Kurzzugriffe
    @property
    def camera(self) -> Camera:
        return self.scene.camera

    @property
    def playback(self) -> Playback:
        return self.scene.playback

    @property
    def trails(self) -> Trails:
        return self.scene.trails

    def tick(self) -> None:
        if not self.playback.paused:
            # In Stücken von höchstens einem Tag, damit die Spuren keinen Tag verpassen
            remaining = self.playback.seconds_per_frame
            while remaining > 0:
                chunk = min(remaining, config.TIMESTEP)
                day_before = self.simulation.day
                self.simulation.advance(chunk)
                remaining -= chunk
                if self.simulation.day != day_before:
                    self.trails.record(self.simulation.bodies, self.simulation.day)
        self.camera.update_follow()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt-API)
        painter = QPainter(self)
        try:
            self.renderer.draw(painter, self.rect(), self.scene)
        finally:
            painter.end()

    # ------------------------------------------------------------------ maus
    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 (Qt-API)
        pos = event.pos()
        zoom_in = event.angleDelta().y() > 0
        self.camera.zoom_at(zoom_in, pos.x(), pos.y(), self.width(), self.height())
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt-API)
        if event.button() == Qt.LeftButton:
            self._press_pos = self._last_drag_pos = event.pos()
            self._dragging = False

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt-API)
        if self._press_pos is None:  # nur während die linke Taste gedrückt ist
            return
        if not self._dragging:
            moved = (event.pos() - self._press_pos).manhattanLength()
            if moved < config.DRAG_THRESHOLD_PX:
                return
            self._dragging = True
            self.setCursor(Qt.ClosedHandCursor)
        delta = event.pos() - self._last_drag_pos
        self._last_drag_pos = event.pos()
        self.camera.pan(delta.x(), delta.y())
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt-API)
        if event.button() != Qt.LeftButton or self._press_pos is None:
            return
        if not self._dragging:  # einfacher Klick -> Körper auswählen / abwählen
            pos = event.pos()
            self.scene.selected = self.camera.pick(
                self.simulation.bodies, pos.x(), pos.y(), self.width(), self.height()
            )
        self._press_pos = None
        self._dragging = False
        self.setCursor(Qt.OpenHandCursor)
        self.update()

    # ---------------------------------------------------------------- tasten
    def _follow(self, body) -> None:
        self.camera.follow = body
        self.scene.selected = body
        self.camera.update_follow()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt-API)
        key = event.key()
        options = self.renderer.options
        if key in TOGGLES:
            setattr(options, TOGGLES[key], not getattr(options, TOGGLES[key]))
        elif key == Qt.Key_Space:
            self.playback.toggle_pause()
        elif key in (Qt.Key_Plus, Qt.Key_Equal):
            self.playback.faster()
        elif key == Qt.Key_Minus:
            self.playback.slower()
        elif key == Qt.Key_M:
            self.camera.realistic = not self.camera.realistic
            self.camera.update_follow()
        elif key == Qt.Key_F2:
            self.translator.toggle()
            self.setWindowTitle(self.translator.t("window_title"))
        elif Qt.Key_0 <= key <= Qt.Key_9:
            index = key - Qt.Key_0  # 0 = Sonne, 1 = Merkur … 9 = Pluto
            if index < len(self.simulation.bodies):
                self._follow(self.simulation.bodies[index])
        elif key == Qt.Key_F:
            if self.scene.selected is not None:
                self._follow(self.scene.selected)
        elif key == Qt.Key_R:
            self.camera.reset()
        elif key == Qt.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
        elif key == Qt.Key_Escape:
            self.close()
            return
        self.update()


def _set_windows_app_id() -> None:
    """Eigenes Taskleisten-Icon unter Windows (statt des Python-Icons)."""
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(config.WINDOWS_APP_ID)


def main() -> int:
    _set_windows_app_id()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()
