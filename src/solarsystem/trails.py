"""Bahnspuren: merkt sich vergangene Positionen der Planeten und Kometen. Ohne GUI."""

from __future__ import annotations

import math
from collections import deque

from . import config
from .physics import Body


class Trails:
    """Speichert pro Körper einen Teil seiner Umlaufbahn.

    Jede Spur deckt `config.TRAIL_ORBIT_FRACTION` eines Umlaufs ab. Damit äußere
    Körper (Pluto, Halley) keine riesigen Listen brauchen, wird nur jeder n-te Tag
    gespeichert, sodass höchstens `config.TRAIL_MAX_POINTS` Punkte entstehen.
    Monde bekommen keine Spur (sie würden die Planetenspur nur verwackeln).
    """

    def __init__(self, bodies: list[Body]) -> None:
        self._points: dict[Body, deque[tuple[float, float]]] = {}
        self._every: dict[Body, int] = {}

        central = max(bodies, key=lambda b: b.mass)
        mu = config.G * central.mass
        for body in bodies:
            if body is central or body.parent is not None:
                continue
            r = math.dist((body.x, body.y, body.z), (central.x, central.y, central.z))
            v_sq = (
                (body.x_vel - central.x_vel) ** 2
                + (body.y_vel - central.y_vel) ** 2
                + (body.z_vel - central.z_vel) ** 2
            )
            inv_a = 2 / r - v_sq / mu  # Vis-Viva-Gleichung
            if inv_a <= 0:
                continue  # offene Bahn
            period_steps = 2 * math.pi * math.sqrt((1 / inv_a) ** 3 / mu) / config.TIMESTEP
            span = period_steps * config.TRAIL_ORBIT_FRACTION
            every = max(1, math.ceil(span / config.TRAIL_MAX_POINTS))
            self._every[body] = every
            self._points[body] = deque(maxlen=max(2, math.ceil(span / every)))

    def record(self, bodies: list[Body], step: int) -> None:
        for body in bodies:
            every = self._every.get(body)
            if every is not None and step % every == 0:
                self._points[body].append((body.x, body.y))

    def points(self, body: Body) -> list[tuple[float, float]]:
        """Gespeicherte Positionen, älteste zuerst (leer für Sonne und Monde)."""
        return list(self._points.get(body, ()))
