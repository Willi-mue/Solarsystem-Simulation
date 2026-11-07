import math
from datetime import datetime, timezone

import numpy as np

from solarsystem import config
from solarsystem.orbits import (
    J2000,
    datetime_from_jd,
    julian_date,
    orbit_points,
    solve_kepler,
    state_from_elements,
)

MU = config.G * 1.98892e30


def test_julian_date_roundtrip():
    moment = datetime(2026, 11, 7, tzinfo=timezone.utc)
    assert julian_date(moment) == 2461351.5
    assert datetime_from_jd(2461351.5) == moment
    assert julian_date(datetime(2000, 1, 1, 12, tzinfo=timezone.utc)) == J2000


def test_solve_kepler_high_eccentricity():
    for e in (0.0, 0.3, 0.967):
        for m in (0.1, 1.0, 3.0, 5.5):
            ecc = solve_kepler(m, e)
            assert math.isclose(
                ecc - e * math.sin(ecc), math.remainder(m, 2 * math.pi), abs_tol=1e-10
            )


def test_circular_orbit_state():
    a = config.AU
    pos, vel = state_from_elements(a, 0.0, 0.0, 0.0, 0.0, 0.0, MU)
    assert math.isclose(math.dist(pos, (0, 0, 0)), a)
    assert math.isclose(math.dist(vel, (0, 0, 0)), math.sqrt(MU / a))


def test_orbit_points_span_perihelion_to_aphelion():
    a, e = 2 * config.AU, 0.5
    pos, vel = state_from_elements(a, e, 0.1, 0.4, 1.2, 0.7, MU)
    pts = orbit_points(pos, vel, MU, 360)
    r = np.hypot(pts[:, 0], pts[:, 1])
    # Projektion in die Ekliptik (Neigung 0,1 rad) verkürzt minimal
    assert math.isclose(r.min(), a * (1 - e), rel_tol=0.01)
    assert math.isclose(r.max(), a * (1 + e), rel_tol=0.01)
    assert np.allclose(pts[0], pts[-1])  # geschlossen
