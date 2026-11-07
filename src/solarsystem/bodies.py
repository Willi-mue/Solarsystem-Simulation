"""Startdaten des Sonnensystems: Planeten, Monde, Komet, Asteroidengürtel.

Planetenpositionen stammen aus den Kepler-Elementen von JPL
(„Approximate Positions of the Planets“, E. M. Standish, gültig 1800–2050):
https://ssd.jpl.nasa.gov/planets/approx_pos.html
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np

from . import config
from .orbits import J2000, state_from_elements
from .physics import Body, MoonOrbit, move_to_center_of_mass_frame


@dataclass(frozen=True)
class PlanetData:
    name: str
    radius: float  # stilisierter Darstellungsradius
    real_radius_km: float
    color: tuple[int, int, int]
    mass: float  # kg
    # Elemente zu J2000 und Änderung pro Jahrhundert:
    # a [AE], e, I [°], L mittlere Länge [°], ϖ Perihellänge [°], Ω Knotenlänge [°]
    elements: tuple[float, float, float, float, float, float]
    rates: tuple[float, float, float, float, float, float]
    has_rings: bool = False


SUN_MASS = 1.98892e30
SUN_REAL_RADIUS_KM = 696_340

PLANETS: tuple[PlanetData, ...] = (
    PlanetData(
        "Mercury", 8, 2_439.7, (169, 169, 169), 3.3011e23,
        (0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593),
        (0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081),
    ),
    PlanetData(
        "Venus", 14, 6_051.8, (218, 165, 32), 4.8675e24,
        (0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255),
        (0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418),
    ),
    PlanetData(
        "Earth", 16, 6_371.0, (0, 102, 204), 5.9722e24,
        (1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0),
        (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0),
    ),
    PlanetData(
        "Mars", 12, 3_389.5, (188, 39, 50), 6.4171e23,
        (1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
        (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343),
    ),
    PlanetData(
        "Jupiter", 25, 69_911, (210, 180, 140), 1.8982e27,
        (5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909),
        (-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106),
    ),
    PlanetData(
        "Saturn", 23, 58_232, (222, 184, 135), 5.6834e26,
        (9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448),
        (-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794),
        has_rings=True,
    ),
    PlanetData(
        "Uranus", 20, 25_362, (173, 216, 230), 8.6810e25,
        (19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503),
        (-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589),
    ),
    PlanetData(
        "Neptune", 20, 24_622, (60, 90, 200), 1.02413e26,
        (30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574),
        (0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664),
    ),
    PlanetData(
        "Pluto", 6, 1_188.3, (200, 200, 200), 1.303e22,
        (39.48211675, 0.24882730, 17.14001206, 238.92903833, 224.06891629, 110.30393684),
        (-0.00031596, 0.00005170, 0.00004818, 145.20780515, -0.04062942, -0.01183482),
    ),
)  # fmt: skip


@dataclass(frozen=True)
class MoonData:
    name: str
    parent: str
    radius: float  # stilisiert
    real_radius_km: float
    color: tuple[int, int, int]
    mass: float
    distance_km: float  # große Halbachse
    period_days: float  # negativ = rückläufig
    # Mittlere Länge zu J2000 [°]. Für den Erdmond aus der Mondtheorie (real),
    # für die übrigen Monde nur ein Näherungswert (Startwinkel nicht exakt).
    longitude_j2000: float


MOONS: tuple[MoonData, ...] = (
    MoonData("Moon", "Earth", 4, 1_737.4, (205, 205, 200), 7.342e22, 384_400, 27.321661, 218.316),
    MoonData("Io", "Jupiter", 3.5, 1_821.6, (230, 205, 110), 8.932e22, 421_700, 1.769138, 163.8),
    MoonData("Europa", "Jupiter", 3.2, 1_560.8, (205, 185, 155), 4.800e22, 671_034, 3.551181, 358.4),
    MoonData("Ganymede", "Jupiter", 4.5, 2_634.1, (165, 155, 145), 1.482e23, 1_070_412, 7.154553, 5.7),
    MoonData("Callisto", "Jupiter", 4.2, 2_410.3, (125, 115, 105), 1.076e23, 1_882_709, 16.689018, 224.8),
    MoonData("Titan", "Saturn", 4.4, 2_574.7, (225, 170, 90), 1.345e23, 1_221_870, 15.945421, 120.0),
    MoonData("Triton", "Neptune", 3.6, 1_353.4, (195, 205, 215), 2.139e22, 354_759, -5.876854, 40.0),
)  # fmt: skip


@dataclass(frozen=True)
class CometData:
    name: str
    radius: float
    real_radius_km: float
    color: tuple[int, int, int]
    mass: float
    a_au: float
    e: float
    inclination: float  # °
    node: float  # °
    arg_perihelion: float  # °
    perihelion_jd: float


HALLEY = CometData(
    "Halley", 3, 5.5, (150, 220, 255), 2.2e14,
    17.834, 0.96714, 162.26, 58.42, 111.33, 2446470.96,  # Perihel 9. Feb. 1986
)  # fmt: skip


def _body_from_state(
    name: str,
    radius: float,
    real_radius_km: float,
    color: tuple[int, int, int],
    mass: float,
    pos: tuple[float, float, float],
    vel: tuple[float, float, float],
    has_rings: bool = False,
) -> Body:
    return Body(
        name,
        pos[0],
        pos[1],
        radius,
        color,
        mass,
        x_vel=vel[0],
        y_vel=vel[1],
        z=pos[2],
        z_vel=vel[2],
        real_radius=real_radius_km * 1000,
        has_rings=has_rings,
    )


def _planet_body(data: PlanetData, centuries: float, mu_sun: float) -> Body:
    a, e, inc, mean_long, peri_long, node = (
        value + rate * centuries for value, rate in zip(data.elements, data.rates, strict=True)
    )
    pos, vel = state_from_elements(
        a * config.AU,
        e,
        math.radians(inc),
        math.radians(node),
        math.radians(peri_long - node),
        math.radians(mean_long - peri_long),
        mu_sun + config.G * data.mass,
    )
    return _body_from_state(
        data.name, data.radius, data.real_radius_km, data.color, data.mass, pos, vel, data.has_rings
    )


def _comet_body(data: CometData, jd: float, mu_sun: float) -> Body:
    a = data.a_au * config.AU
    mean_motion = math.sqrt(mu_sun / a**3)  # rad/s
    pos, vel = state_from_elements(
        a,
        data.e,
        math.radians(data.inclination),
        math.radians(data.node),
        math.radians(data.arg_perihelion),
        mean_motion * (jd - data.perihelion_jd) * 86400,
        mu_sun,
    )
    return _body_from_state(
        data.name, data.radius, data.real_radius_km, data.color, data.mass, pos, vel
    )


def create_solar_system(jd: float = J2000) -> list[Body]:
    """Sonne, Planeten, Komet und Monde zum Julianischen Datum `jd`.

    Reihenfolge: Sonne, Merkur … Pluto (Index 0–9, passend zu den Zifferntasten),
    danach Halley und die Monde. Jeder Aufruf erzeugt frische Objekte.
    """
    centuries = (jd - J2000) / 36525
    mu_sun = config.G * SUN_MASS

    sun = Body("Sun", 0.0, 0.0, 30, (255, 204, 0), SUN_MASS, real_radius=SUN_REAL_RADIUS_KM * 1000)
    bodies = [sun]
    bodies += [_planet_body(p, centuries, mu_sun) for p in PLANETS]
    bodies.append(_comet_body(HALLEY, jd, mu_sun))
    move_to_center_of_mass_frame(bodies)

    by_name = {b.name: b for b in bodies}
    rank: dict[str, int] = {}
    days = jd - J2000
    for m in sorted(MOONS, key=lambda m: m.distance_km):
        parent = by_name[m.parent]
        phase = math.radians(m.longitude_j2000 + 360 * days / m.period_days)
        bodies.append(
            Body(
                m.name,
                parent.x,
                parent.y,
                m.radius,
                m.color,
                m.mass,
                real_radius=m.real_radius_km * 1000,
                parent=parent,
                orbit=MoonOrbit(m.distance_km * 1000, m.period_days * 86400, phase),
                moon_rank=rank.get(m.parent, 0),
            )
        )
        rank[m.parent] = rank.get(m.parent, 0) + 1
    return bodies


def create_asteroids(
    sun: Body, count: int = config.ASTEROID_COUNT, seed: int = config.ASTEROID_SEED
) -> tuple[np.ndarray, np.ndarray]:
    """Zufälliger Hauptgürtel (2,1–3,3 AE) mit Lücken an den Kirkwood-Resonanzen."""
    rng = random.Random(seed)
    mu = config.G * sun.mass
    kirkwood_gaps = (2.50, 2.82, 2.95)
    positions, velocities = [], []
    while len(positions) < count:
        a = rng.uniform(2.1, 3.3)
        if any(abs(a - gap) < 0.035 for gap in kirkwood_gaps):
            continue
        pos, vel = state_from_elements(
            a * config.AU,
            rng.uniform(0.0, 0.18),
            math.radians(abs(rng.gauss(0, 6))),
            rng.uniform(0, 2 * math.pi),
            rng.uniform(0, 2 * math.pi),
            rng.uniform(0, 2 * math.pi),
            mu,
        )
        positions.append((sun.x + pos[0], sun.y + pos[1], sun.z + pos[2]))
        velocities.append((sun.x_vel + vel[0], sun.y_vel + vel[1], sun.z_vel + vel[2]))
    return np.array(positions).reshape(-1, 3), np.array(velocities).reshape(-1, 3)
