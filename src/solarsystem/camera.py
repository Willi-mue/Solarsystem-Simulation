"""Ansicht: Zoom, Verschieben, Verfolgen, Maßstab und Bildschirm-Layout. Ohne GUI.

Blick von „oben“ (ekliptikaler Nordpol): Die Planeten laufen gegen den
Uhrzeigersinn, die Bildschirm-y-Achse ist dafür gespiegelt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import config
from .physics import Body

ScreenPos = tuple[float, float, float]  # x, y, Radius in Pixeln


@dataclass
class Camera:
    zoom: float = config.ZOOM_DEFAULT
    center_x: float = 0.0  # Weltposition (Meter) in der Bildschirmmitte
    center_y: float = 0.0
    follow: Body | None = None  # Körper, auf den die Ansicht zentriert bleibt
    realistic: bool = False  # True = echte Größen, False = stilisiert

    # ------------------------------------------------------------------ zoom
    def zoom_in(self) -> None:
        self.zoom = self._clamp(self.zoom * config.ZOOM_STEP)

    def zoom_out(self) -> None:
        self.zoom = self._clamp(self.zoom / config.ZOOM_STEP)

    def zoom_at(self, zoom_in: bool, sx: float, sy: float, width: float, height: float) -> None:
        """Zoomen, sodass der Weltpunkt unter (sx, sy) an derselben Stelle bleibt.

        Beim Verfolgen eines Körpers wird zur Mitte gezoomt (Körper bleibt zentriert).
        """
        if self.follow is not None:
            self.zoom_in() if zoom_in else self.zoom_out()
            return
        wx, wy = self.screen_to_world(sx, sy, width, height)
        self.zoom_in() if zoom_in else self.zoom_out()
        factor = config.SCALE * self.zoom
        self.center_x = wx - (sx - width / 2) / factor
        self.center_y = wy + (sy - height / 2) / factor

    @staticmethod
    def _clamp(zoom: float) -> float:
        return max(config.ZOOM_MIN, min(zoom, config.ZOOM_MAX))

    # ------------------------------------------------------------ pan/follow
    def pan(self, dx_px: float, dy_px: float) -> None:
        """Ansicht um Bildschirmpixel verschieben (beendet das Verfolgen)."""
        self.follow = None
        factor = config.SCALE * self.zoom
        self.center_x -= dx_px / factor
        self.center_y += dy_px / factor

    def update_follow(self) -> None:
        target = self.follow
        if target is None:
            return
        # Stilisiert stehen Monde nicht an ihrer echten Position -> Planet zentrieren
        if target.parent is not None and not self.realistic:
            target = target.parent
        self.center_x, self.center_y = target.x, target.y

    def reset(self) -> None:
        self.zoom = config.ZOOM_DEFAULT
        self.center_x = self.center_y = 0.0
        self.follow = None

    # ------------------------------------------------------------ conversion
    def world_to_screen(
        self, x: float, y: float, width: float, height: float
    ) -> tuple[float, float]:
        """Weltposition (Meter) -> Bildschirmposition (Pixel)."""
        factor = config.SCALE * self.zoom
        return (x - self.center_x) * factor + width / 2, height / 2 - (y - self.center_y) * factor

    def world_to_screen_array(
        self, xs: np.ndarray, ys: np.ndarray, width: float, height: float
    ) -> tuple[np.ndarray, np.ndarray]:
        factor = config.SCALE * self.zoom
        return (xs - self.center_x) * factor + width / 2, height / 2 - (ys - self.center_y) * factor

    def screen_to_world(
        self, sx: float, sy: float, width: float, height: float
    ) -> tuple[float, float]:
        factor = config.SCALE * self.zoom
        return (sx - width / 2) / factor + self.center_x, (height / 2 - sy) / factor + self.center_y

    # ---------------------------------------------------------------- layout
    def body_radius_px(self, body: Body) -> float:
        if self.realistic:
            return max(body.real_radius * config.SCALE * self.zoom, config.MIN_REAL_RADIUS_PX)
        # Stilisiert: bis Zoom 1 linear, danach nur noch langsam wachsen
        growth = self.zoom if self.zoom <= 1 else self.zoom**config.STYLIZED_GROWTH
        return max(body.radius * config.RADIUS_SCALE / 2 * growth, config.MIN_BODY_RADIUS_PX)

    def layout(self, bodies: list[Body], width: float, height: float) -> dict[Body, ScreenPos]:
        """Bildschirmposition und -radius aller sichtbaren Körper.

        Monde: Stilisiert werden sie außerhalb des (vergrößerten) Planeten
        aufgefächert, Richtung bleibt echt. Bei echten Größen werden sie
        ausgeblendet, solange sie optisch im Planeten verschwinden würden.
        """
        factor = config.SCALE * self.zoom
        result: dict[Body, ScreenPos] = {}
        for body in bodies:
            r = self.body_radius_px(body)
            if body.parent is None:
                result[body] = (*self.world_to_screen(body.x, body.y, width, height), r)
                continue
            parent_pos = result.get(body.parent)
            if parent_pos is None:
                continue
            px, py, pr = parent_pos
            dx, dy = body.x - body.parent.x, body.y - body.parent.y
            real = math.hypot(dx, dy)
            real_px = real * factor
            if self.realistic:
                if real_px < pr + r + 2:
                    continue
                dist = real_px
            else:
                dist = max(real_px, pr * (1.6 + 0.75 * body.moon_rank) + r)
            ux, uy = (dx / real, dy / real) if real else (1.0, 0.0)
            result[body] = (px + ux * dist, py - uy * dist, r)
        return result

    def pick(
        self, bodies: list[Body], sx: float, sy: float, width: float, height: float
    ) -> Body | None:
        """Körper unter dem Mauszeiger (mit etwas Toleranz), sonst None."""
        best, best_dist = None, math.inf
        for body, (bx, by, r) in self.layout(bodies, width, height).items():
            dist = math.hypot(bx - sx, by - sy)
            if dist <= r + config.PICK_TOLERANCE_PX and dist < best_dist:
                best, best_dist = body, dist
        return best
