"""Smoke-Tests: Fenster erzeugen, zeichnen und bedienen (ohne echten Bildschirm)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PyQt5.QtGui import QMouseEvent  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402

from .conftest import JD, by_name  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(qapp):
    from solarsystem.app import MainWindow

    w = MainWindow(start_jd=JD)
    w.timer.stop()
    w.resize(1920, 1080)
    yield w
    w.close()


def _screen_pos(window, body):
    x, y, _ = window.camera.layout(window.simulation.bodies, window.width(), window.height())[body]
    return QPoint(round(x), round(y))


def test_window_ticks_and_renders(window):
    from solarsystem.app import ICON_PATH

    window.tick()
    assert window.simulation.day == 1
    assert not window.grab().isNull()
    assert ICON_PATH.is_file()


def test_pause_and_speed_keys(window):
    QTest.keyClick(window, Qt.Key_Plus)
    window.tick()
    assert window.simulation.day == 2
    QTest.keyClick(window, Qt.Key_Space)
    window.tick()
    assert window.simulation.day == 2


def test_slow_speeds(window):
    for _ in range(4):
        QTest.keyClick(window, Qt.Key_Minus)
    assert window.playback.minutes_per_frame == 60
    for _ in range(23):
        window.tick()
    assert window.simulation.day == 0
    window.tick()
    assert window.simulation.day == 1

    for _ in range(20):
        QTest.keyClick(window, Qt.Key_Minus)
    assert window.playback.minutes_per_frame == 1
    start = window.simulation.elapsed
    for _ in range(30):
        window.tick()
    assert window.simulation.elapsed - start == 30 * 60
    assert not window.grab().isNull()  # HUD mit Uhrzeit


def test_number_key_follows_body(window):
    QTest.keyClick(window, Qt.Key_3)
    earth = window.simulation.bodies[3]
    assert earth.name == "Earth"
    assert window.camera.follow is earth and window.scene.selected is earth
    window.tick()
    assert _screen_pos(window, earth) == QPoint(window.width() // 2, window.height() // 2)
    assert not window.grab().isNull()  # mit Info-Panel und "Folge"-Zeile
    QTest.keyClick(window, Qt.Key_R)
    assert window.camera.follow is None


def test_click_selects_then_f_follows(window):
    mars = by_name(window.simulation.bodies, "Mars")
    QTest.mouseClick(window, Qt.LeftButton, pos=_screen_pos(window, mars))
    assert window.scene.selected is mars
    QTest.keyClick(window, Qt.Key_F)
    assert window.camera.follow is mars
    QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(5, 5))
    assert window.scene.selected is None


def test_drag_pans_view(window):
    start = QPoint(300, 300)
    QTest.mousePress(window, Qt.LeftButton, pos=start)
    for step in range(1, 6):
        # QTest.mouseMove erzeugt offscreen kein Event -> direkt senden
        pos = start + QPoint(20 * step, 0)
        move = QMouseEvent(
            QEvent.MouseMove, QPointF(pos), Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        QtWidgets.QApplication.sendEvent(window, move)
    QTest.mouseRelease(window, Qt.LeftButton, pos=start + QPoint(100, 0))
    sx, _ = window.camera.world_to_screen(0, 0, window.width(), window.height())
    assert sx == pytest.approx(window.width() / 2 + 100)
    assert window.scene.selected is None  # Ziehen ist kein Klick


def test_scale_language_and_asteroid_keys(window):
    QTest.keyClick(window, Qt.Key_M)
    assert window.camera.realistic
    QTest.keyClick(window, Qt.Key_F2)
    assert window.translator.language == "en"
    assert window.windowTitle() == "Solar System"
    QTest.keyClick(window, Qt.Key_A)
    assert not window.renderer.options.show_asteroids
    assert not window.grab().isNull()
