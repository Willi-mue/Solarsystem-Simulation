"""Zeichnet den aktuellen Simulationszustand. Verändert ihn nie."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np
from PyQt5.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
)

from . import config
from .camera import Camera, ScreenPos
from .i18n import Translator
from .orbits import orbit_points
from .physics import Body, Simulation
from .playback import Playback
from .trails import Trails

RING_OUTER = 2.35  # Außenradius der Saturnringe relativ zum Planetenradius
RING_TILT = 0.32  # Verhältnis Höhe/Breite der Ring-Ellipse


@dataclass
class RenderOptions:
    show_trails: bool = True
    show_orbits: bool = True
    show_labels: bool = True
    show_help: bool = True
    show_asteroids: bool = True


@dataclass
class Scene:
    """Alles, was für ein Bild gebraucht wird."""

    simulation: Simulation
    camera: Camera
    trails: Trails
    playback: Playback
    translator: Translator
    selected: Body | None = None


class Renderer:
    def __init__(self) -> None:
        self.options = RenderOptions()
        self.title_font = QFont(config.UI_FONT_FAMILY, 15, QFont.DemiBold)
        self.text_font = QFont(config.UI_FONT_FAMILY, 10)
        self.label_font = QFont(config.UI_FONT_FAMILY, 9)
        self._background: QPixmap | None = None
        self._orbit_cache: dict[Body, tuple[int, np.ndarray | None]] = {}

    # ------------------------------------------------------------------ public
    def draw(self, painter: QPainter, rect: QRect, scene: Scene) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, self._background_for(rect.size()))

        sim, camera = scene.simulation, scene.camera
        w, h = rect.width(), rect.height()
        layout = camera.layout(sim.bodies, w, h)
        sun = sim.central

        if self.options.show_orbits:
            self._draw_orbits(painter, sim, camera, layout, w, h)
        if self.options.show_trails:
            self._draw_trails(painter, sim.bodies, scene.trails, camera, w, h)
        if self.options.show_asteroids:
            self._draw_asteroids(painter, sim, camera, w, h)

        sun_pos = QPointF(*layout[sun][:2])
        for body, (sx, sy, radius) in layout.items():
            if body is sun:
                self._draw_sun(painter, QPointF(sx, sy), radius)
            else:
                self._draw_planet(painter, body, QPointF(sx, sy), radius, sun_pos)

        if self.options.show_labels:
            self._draw_labels(painter, layout, sun, scene.translator)
        if scene.selected is not None:
            if scene.selected in layout:
                self._draw_selection(painter, layout[scene.selected])
            self._draw_info(painter, rect, scene.selected, sim, scene.translator)
        self._draw_hud(painter, scene)
        if self.options.show_help:
            self._draw_help(painter, rect, scene.translator)

    # -------------------------------------------------------------- background
    def _background_for(self, size: QSize) -> QPixmap:
        if self._background is None or self._background.size() != size:
            self._background = self._make_background(size)
        return self._background

    @staticmethod
    def _make_background(size: QSize) -> QPixmap:
        w, h = size.width(), size.height()
        pixmap = QPixmap(size)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QRadialGradient(w / 2, h / 2, math.hypot(w, h) / 2)
        gradient.setColorAt(0.0, QColor(14, 18, 38))
        gradient.setColorAt(1.0, QColor(2, 2, 6))
        painter.fillRect(0, 0, w, h, gradient)

        rng = random.Random(42)  # fester Seed -> immer derselbe Himmel
        painter.setPen(Qt.NoPen)
        for _ in range(int(w * h * config.STAR_DENSITY)):
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            brightness = rng.randint(70, 255)
            tint = rng.choice(((255, 255, 255), (200, 215, 255), (255, 235, 210)))
            color = QColor(*(int(c * brightness / 255) for c in tint))
            r = 1.4 if rng.random() < 0.06 else rng.uniform(0.4, 0.9)
            if r > 1:  # einzelne helle Sterne mit leichtem Schimmer
                halo = QColor(color)
                halo.setAlpha(40)
                painter.setBrush(halo)
                painter.drawEllipse(QPointF(x, y), r * 3, r * 3)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(x, y), r, r)
        painter.end()
        return pixmap

    # ----------------------------------------------------- orbits/trails/belt
    def _orbit_shape(self, body: Body, sun: Body, day: int) -> np.ndarray | None:
        """Bahnellipse relativ zur Sonne (gecacht, alle paar Tage neu berechnet)."""
        cached = self._orbit_cache.get(body)
        if cached is None or abs(day - cached[0]) >= config.ORBIT_REFRESH_DAYS:
            pts = orbit_points(
                (body.x - sun.x, body.y - sun.y, body.z - sun.z),
                (body.x_vel - sun.x_vel, body.y_vel - sun.y_vel, body.z_vel - sun.z_vel),
                config.G * (sun.mass + body.mass),
                config.ORBIT_SAMPLES,
            )
            cached = (day, pts)
            self._orbit_cache[body] = cached
        return cached[1]

    def _draw_orbits(
        self,
        painter: QPainter,
        sim: Simulation,
        camera: Camera,
        layout: dict[Body, ScreenPos],
        w: int,
        h: int,
    ) -> None:
        painter.setBrush(Qt.NoBrush)
        sun = sim.central
        for body in sim.bodies:
            if body is sun:
                continue
            color = QColor(*body.color)
            if body.parent is not None:  # Mondbahn: Kreis um den Planeten
                if body in layout and body.parent in layout:
                    px, py, _ = layout[body.parent]
                    mx, my, _ = layout[body]
                    color.setAlpha(45)
                    painter.setPen(QPen(color, 1))
                    r = math.hypot(mx - px, my - py)
                    painter.drawEllipse(QPointF(px, py), r, r)
                continue
            shape = self._orbit_shape(body, sun, sim.day)
            if shape is None:
                continue
            xs, ys = camera.world_to_screen_array(shape[:, 0] + sun.x, shape[:, 1] + sun.y, w, h)
            color.setAlpha(34)
            painter.setPen(QPen(color, 1))
            painter.drawPolyline(_polygon(xs, ys))

    @staticmethod
    def _draw_trails(
        painter: QPainter, bodies: list[Body], trails: Trails, camera: Camera, w: int, h: int
    ) -> None:
        segments = config.TRAIL_FADE_SEGMENTS
        for body in bodies:
            world = trails.points(body)
            if len(world) < 2:
                continue
            world.append((body.x, body.y))  # Spur endet genau am Körper
            pts = [QPointF(*camera.world_to_screen(x, y, w, h)) for x, y in world]

            # Ältere Abschnitte blasser zeichnen -> Spur verblasst nach hinten.
            chunk = max(2, math.ceil(len(pts) / segments))
            for i, start in enumerate(range(0, len(pts) - 1, chunk - 1)):
                color = QColor(*body.color)
                color.setAlpha(int(25 + 150 * (i + 1) / segments))
                pen = QPen(color, 1.6)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.drawPolyline(QPolygonF(pts[start : start + chunk]))

    @staticmethod
    def _draw_asteroids(painter: QPainter, sim: Simulation, camera: Camera, w: int, h: int) -> None:
        ast = sim.asteroid_positions
        if not len(ast):
            return
        xs, ys = camera.world_to_screen_array(ast[:, 0], ast[:, 1], w, h)
        visible = (xs > -2) & (xs < w + 2) & (ys > -2) & (ys < h + 2)
        if not visible.any():
            return
        pen = QPen(QColor(175, 165, 150, 150), 1.7)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawPoints(_polygon(xs[visible], ys[visible]))

    # ------------------------------------------------------------------ bodies
    @staticmethod
    def _draw_sun(painter: QPainter, pos: QPointF, radius: float) -> None:
        painter.setPen(Qt.NoPen)

        glow = QRadialGradient(pos, radius * 3.2)
        glow.setColorAt(0.0, QColor(255, 220, 130, 150))
        glow.setColorAt(0.3, QColor(255, 170, 50, 60))
        glow.setColorAt(1.0, QColor(255, 120, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(pos, radius * 3.2, radius * 3.2)

        disk = QRadialGradient(pos, radius)
        disk.setColorAt(0.0, QColor(255, 252, 230))
        disk.setColorAt(0.6, QColor(255, 214, 70))
        disk.setColorAt(1.0, QColor(255, 160, 20))
        painter.setBrush(QBrush(disk))
        painter.drawEllipse(pos, radius, radius)

    def _draw_planet(
        self, painter: QPainter, body: Body, pos: QPointF, radius: float, sun_pos: QPointF
    ) -> None:
        if body.has_rings:
            self._draw_rings(painter, pos, radius, front=False)

        # Beleuchtung: hellster Punkt auf der Seite, die zur Sonne zeigt.
        dx, dy = sun_pos.x() - pos.x(), sun_pos.y() - pos.y()
        length = math.hypot(dx, dy) or 1.0
        focal = QPointF(pos.x() + dx / length * radius * 0.6, pos.y() + dy / length * radius * 0.6)

        base = QColor(*body.color)
        shade = QRadialGradient(pos, radius * 1.6, focal)
        shade.setColorAt(0.0, base.lighter(150))
        shade.setColorAt(0.45, base)
        shade.setColorAt(1.0, base.darker(500))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(shade))
        painter.drawEllipse(pos, radius, radius)

        if body.has_rings:
            self._draw_rings(painter, pos, radius, front=True)

    @staticmethod
    def _draw_rings(painter: QPainter, pos: QPointF, radius: float, front: bool) -> None:
        """Ringe in zwei Hälften: hintere vor dem Planeten zeichnen, vordere danach."""
        painter.save()
        painter.translate(pos)
        painter.rotate(-18)
        painter.setPen(Qt.NoPen)
        # Obere Hälfte (0°–180°) liegt hinter dem Planeten, untere (180°–360°) davor.
        # Die hintere Hälfte ist 2° breiter, damit an den Spitzen keine Naht entsteht.
        start, span = (180.0, 180.0) if front else (-1.0, 182.0)
        # Zwei deckende Ringbänder mit Lücke dazwischen (Cassini-Teilung).
        for inner, outer, color in (
            (1.3, 1.75, QColor(150, 136, 112)),
            (1.85, RING_OUTER, QColor(196, 178, 140)),
        ):
            painter.setBrush(color)
            painter.drawPath(_half_ring(radius * inner, radius * outer, start, span))
        painter.restore()

    # ---------------------------------------------------------------- overlays
    def _draw_labels(
        self, painter: QPainter, layout: dict[Body, ScreenPos], sun: Body, tr: Translator
    ) -> None:
        painter.setFont(self.label_font)
        sun_x, sun_y, sun_r = layout[sun]
        placed: list[tuple[float, float]] = []
        for body, (x, y, radius) in layout.items():
            if body is not sun and math.hypot(x - sun_x, y - sun_y) < sun_r + 18:
                continue  # würde in der Sonne verschwinden
            reach = radius * RING_OUTER if body.has_rings else radius
            ax, ay = x + reach + 6, y + 4
            if any(abs(ax - px) < 50 and abs(ay - py) < 14 for px, py in placed):
                continue  # überlappt ein anderes Label
            alpha = 150 if body.parent is not None else 190
            painter.setPen(QColor(205, 215, 235, alpha))
            painter.drawText(QPointF(ax, ay), tr.name(body.name))
            placed.append((ax, ay))

    def _draw_panel(self, painter: QPainter, panel: QRectF) -> None:
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.setBrush(QColor(255, 255, 255, 16))
        painter.drawRoundedRect(panel, 10, 10)

    def _draw_hud(self, painter: QPainter, scene: Scene) -> None:
        sim, camera, playback, tr = scene.simulation, scene.camera, scene.playback, scene.translator
        years = sim.elapsed / (365.25 * 86400)
        speed = tr.t("paused") if playback.paused else tr.speed(playback.minutes_per_frame)
        zoom = tr.number(camera.zoom, 2 if camera.zoom < 100 else 0)
        scale = tr.t("scale_real" if camera.realistic else "scale_stylized")
        muted = QColor(170, 180, 205)
        lines = [
            (
                f"{tr.t('day')} {tr.number(sim.day)}   ·   {tr.number(years, 2)} {tr.t('years')}",
                muted,
            ),
            (f"{speed}   ·   Zoom {zoom}×   ·   {scale}", muted),
        ]
        if camera.follow is not None:
            follow = tr.t("following", name=tr.name(camera.follow.name))
            lines.append((follow, QColor(*camera.follow.color).lighter(130)))

        self._draw_panel(painter, QRectF(24, 24, 400, 56 + 24 * len(lines)))
        painter.setFont(self.title_font)
        painter.setPen(QColor(240, 244, 255))
        show_time = playback.minutes_per_frame < 1440
        painter.drawText(QPointF(42, 56), tr.date(sim.current_jd, with_time=show_time))
        painter.setFont(self.text_font)
        for i, (text, color) in enumerate(lines):
            painter.setPen(color)
            painter.drawText(QPointF(42, 82 + 24 * i), text)

    def _draw_help(self, painter: QPainter, rect: QRect, tr: Translator) -> None:
        painter.setFont(self.text_font)
        painter.setPen(QColor(170, 180, 205, 150))
        for i, key in enumerate(("help_1", "help_2")):
            top = rect.bottom() - 52 + 22 * i
            painter.drawText(QRectF(rect.left(), top, rect.width(), 20), Qt.AlignCenter, tr.t(key))

    @staticmethod
    def _draw_selection(painter: QPainter, screen: ScreenPos) -> None:
        x, y, radius = screen
        pen = QPen(QColor(255, 255, 255, 170), 1.2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(x, y), radius + 6, radius + 6)

    def _draw_info(
        self, painter: QPainter, rect: QRect, body: Body, sim: Simulation, tr: Translator
    ) -> None:
        rows = [
            (tr.t("mass"), tr.mass(body.mass)),
            (tr.t("radius"), f"{tr.number(body.real_radius / 1000)} km"),
        ]
        if body is not sim.central:
            ref = body.parent or sim.central
            dist = math.dist((body.x, body.y, body.z), (ref.x, ref.y, ref.z))
            speed = math.dist(
                (body.x_vel, body.y_vel, body.z_vel), (ref.x_vel, ref.y_vel, ref.z_vel)
            )
            if body.parent is not None:
                dist_text = f"{tr.number(dist / 1000)} km"
            else:
                dist_text = f"{tr.number(dist / config.AU, 3)} {tr.t('au')}"
            rows += [
                (tr.t("distance_to", name=tr.name(ref.name)), dist_text),
                (tr.t("orbital_speed"), f"{tr.number(speed / 1000, 2)} km/s"),
            ]

        panel = QRectF(rect.right() - 24 - 320, 24, 320, 56 + 24 * len(rows))
        self._draw_panel(painter, panel)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*body.color))
        painter.drawEllipse(QPointF(panel.left() + 26, panel.top() + 27), 6, 6)
        painter.setFont(self.title_font)
        painter.setPen(QColor(240, 244, 255))
        painter.drawText(QPointF(panel.left() + 42, panel.top() + 33), tr.name(body.name))

        painter.setFont(self.text_font)
        for i, (label, value) in enumerate(rows):
            y = panel.top() + 62 + 24 * i
            painter.setPen(QColor(150, 160, 185))
            painter.drawText(QPointF(panel.left() + 18, y), label)
            painter.setPen(QColor(230, 236, 250))
            value_rect = QRectF(panel.left(), y - 16, panel.width() - 18, 20)
            painter.drawText(value_rect, Qt.AlignRight | Qt.AlignVCenter, value)


def _polygon(xs: np.ndarray, ys: np.ndarray) -> QPolygonF:
    return QPolygonF([QPointF(x, y) for x, y in zip(xs.tolist(), ys.tolist(), strict=True)])


def _half_ring(inner: float, outer: float, start_deg: float, span: float) -> QPainterPath:
    """Ausschnitt eines elliptischen Kreisrings als geschlossene Fläche."""
    outer_rect = QRectF(-outer, -outer * RING_TILT, 2 * outer, 2 * outer * RING_TILT)
    inner_rect = QRectF(-inner, -inner * RING_TILT, 2 * inner, 2 * inner * RING_TILT)
    path = QPainterPath()
    path.arcMoveTo(outer_rect, start_deg)
    path.arcTo(outer_rect, start_deg, span)
    path.arcTo(inner_rect, start_deg + span, -span)
    path.closeSubpath()
    return path
