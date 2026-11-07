"""Bahnmechanik: Kepler-Elemente <-> Zustandsvektoren, Julianisches Datum. Ohne GUI."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import numpy as np

J2000 = 2451545.0  # Julianisches Datum von 2000-01-01 12:00 TT
J2000_DATETIME = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)

Vec3 = tuple[float, float, float]


def julian_date(moment: datetime) -> float:
    """Julianisches Datum eines (zeitzonenbewussten) Zeitpunkts."""
    return moment.timestamp() / 86400 + 2440587.5


def datetime_from_jd(jd: float) -> datetime:
    return J2000_DATETIME + timedelta(days=jd - J2000)


def solve_kepler(mean_anomaly: float, e: float) -> float:
    """Löst die Kepler-Gleichung M = E - e·sin(E) nach der exzentrischen Anomalie E."""
    m = math.remainder(mean_anomaly, 2 * math.pi)
    ecc_anomaly = m if e < 0.8 else math.pi
    for _ in range(100):
        delta = (ecc_anomaly - e * math.sin(ecc_anomaly) - m) / (1 - e * math.cos(ecc_anomaly))
        ecc_anomaly -= delta
        if abs(delta) < 1e-13:
            break
    return ecc_anomaly


def state_from_elements(
    a: float,
    e: float,
    inclination: float,
    node: float,
    arg_periapsis: float,
    mean_anomaly: float,
    mu: float,
) -> tuple[Vec3, Vec3]:
    """Position (m) und Geschwindigkeit (m/s) aus Bahnelementen.

    `a` in Metern, alle Winkel in Radiant, `mu` = G·(M + m). Ergebnis im
    ekliptikalen Koordinatensystem relativ zum Zentralkörper.
    """
    ecc_anomaly = solve_kepler(mean_anomaly, e)
    cos_e, sin_e = math.cos(ecc_anomaly), math.sin(ecc_anomaly)
    b = math.sqrt(1 - e * e)
    n = math.sqrt(mu / a**3)
    f = 1 - e * cos_e

    # in der Bahnebene (x zeigt zum Perihel)
    x, y = a * (cos_e - e), a * b * sin_e
    vx, vy = -a * n * sin_e / f, a * n * b * cos_e / f

    co, so = math.cos(node), math.sin(node)
    ci, si = math.cos(inclination), math.sin(inclination)
    cw, sw = math.cos(arg_periapsis), math.sin(arg_periapsis)
    r11, r12 = co * cw - so * sw * ci, -co * sw - so * cw * ci
    r21, r22 = so * cw + co * sw * ci, -so * sw + co * cw * ci
    r31, r32 = sw * si, cw * si

    pos = (r11 * x + r12 * y, r21 * x + r22 * y, r31 * x + r32 * y)
    vel = (r11 * vx + r12 * vy, r21 * vx + r22 * vy, r31 * vx + r32 * vy)
    return pos, vel


def orbit_points(rel_pos: Vec3, rel_vel: Vec3, mu: float, samples: int) -> np.ndarray | None:
    """Punkte (x, y) der aktuellen Kepler-Ellipse relativ zum Zentralkörper.

    Gleichmäßig in der exzentrischen Anomalie verteilt, damit auch stark
    exzentrische Bahnen (Halley) überall glatt aussehen. None bei offenen Bahnen.
    """
    r = np.asarray(rel_pos, dtype=float)
    v = np.asarray(rel_vel, dtype=float)
    h = np.cross(r, v)
    h_norm = np.linalg.norm(h)
    r_norm = np.linalg.norm(r)
    if h_norm == 0 or r_norm == 0:
        return None
    e_vec = np.cross(v, h) / mu - r / r_norm
    e = float(np.linalg.norm(e_vec))
    if e >= 1:
        return None
    a = (h_norm**2 / mu) / (1 - e * e)
    ex = e_vec / e if e > 1e-9 else r / r_norm
    q = np.cross(h / h_norm, ex)

    ecc = np.linspace(0, 2 * np.pi, samples + 1)
    px = a * (np.cos(ecc) - e)
    py = a * math.sqrt(1 - e * e) * np.sin(ecc)
    pts = np.outer(px, ex) + np.outer(py, q)
    return pts[:, :2]
