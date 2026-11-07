import math

import numpy as np

from solarsystem import config
from solarsystem.bodies import create_asteroids, create_solar_system
from solarsystem.physics import Simulation

from .conftest import JD, by_name


def _run(steps: int, asteroids: bool = False) -> Simulation:
    bodies = create_solar_system(JD)
    sim = Simulation(bodies, create_asteroids(bodies[0]) if asteroids else None, start_jd=JD)
    for _ in range(steps):
        sim.step()
    return sim


def _heliocentric(body, sun):
    return body.x - sun.x, body.y - sun.y, body.z - sun.z


def test_simulation_is_deterministic():
    a, b = _run(200, asteroids=True), _run(200, asteroids=True)
    for body_a, body_b in zip(a.bodies, b.bodies, strict=True):
        assert (body_a.x, body_a.y, body_a.z) == (body_b.x, body_b.y, body_b.z)
    assert np.array_equal(a.asteroid_positions, b.asteroid_positions)


def test_earth_position_matches_date(bodies):
    """Am 7. November steht die Sonne bei ~225° → die Erde heliozentrisch bei ~45°."""
    sun, earth = by_name(bodies, "Sun"), by_name(bodies, "Earth")
    x, y, _ = _heliocentric(earth, sun)
    longitude = math.degrees(math.atan2(y, x)) % 360
    assert 42 < longitude < 47
    assert 0.98 < math.hypot(x, y) / config.AU < 1.0  # kurz vor dem Perihel im Januar


def test_earth_returns_after_one_year():
    sim = Simulation(create_solar_system(JD), start_jd=JD)
    sun, earth = by_name(sim.bodies, "Sun"), by_name(sim.bodies, "Earth")
    start = _heliocentric(earth, sun)
    for _ in range(365):
        sim.step()
    assert math.dist(start, _heliocentric(earth, sun)) < 0.02 * config.AU


def test_momentum_is_zero():
    sim = _run(300)
    momentum = np.sum((sim.gm / config.G)[:, None] * sim.vel, axis=0)
    sun = by_name(sim.bodies, "Sun")
    assert np.all(np.abs(momentum) < 1e-6 * sun.mass)


def test_energy_is_conserved_over_fifty_years():
    sim = Simulation(create_solar_system(JD), start_jd=JD)
    e0 = sim.total_energy()
    for _ in range(365 * 50):
        sim.step()
    assert abs(sim.total_energy() - e0) / abs(e0) < 1e-6


def test_mercury_stays_between_perihelion_and_aphelion():
    sim = Simulation(create_solar_system(JD), start_jd=JD)
    sun, mercury = by_name(sim.bodies, "Sun"), by_name(sim.bodies, "Mercury")
    distances = []
    for _ in range(365 * 5):
        sim.step()
        distances.append(math.dist(_heliocentric(mercury, sun), (0, 0, 0)) / config.AU)
    assert 0.300 < min(distances) < 0.315  # Perihel 0,307 AE
    assert 0.460 < max(distances) < 0.472  # Aphel 0,467 AE


def test_halley_is_retrograde_and_far_out(bodies):
    sun, halley = by_name(bodies, "Sun"), by_name(bodies, "Halley")
    x, y, _ = _heliocentric(halley, sun)
    vx, vy = halley.x_vel - sun.x_vel, halley.y_vel - sun.y_vel
    assert x * vy - y * vx < 0  # Drehimpuls zeigt nach Süden → rückläufig
    assert math.hypot(x, y) / config.AU > 30  # Aphel war Ende 2023


def test_moons_follow_their_planets():
    sim = _run(10)
    for moon in sim.moons:
        distance = math.dist(
            (moon.x, moon.y, moon.z), (moon.parent.x, moon.parent.y, moon.parent.z)
        )
        assert math.isclose(distance, moon.orbit.distance, rel_tol=1e-9)


def test_moon_completes_orbit_in_its_period():
    sim = Simulation(create_solar_system(JD), start_jd=JD)
    moon = by_name(sim.bodies, "Moon")
    angle = math.atan2(moon.y - moon.parent.y, moon.x - moon.parent.x)
    for _ in range(27):
        sim.step()
    later = math.atan2(moon.y - moon.parent.y, moon.x - moon.parent.x)
    # 27 von 27,32 Tagen -> knapp ein voller Umlauf, also ~4° vor dem Startwinkel
    assert -0.15 < math.remainder(later - angle, 2 * math.pi) < 0


def test_asteroids_stay_in_belt():
    sim = _run(365 * 2, asteroids=True)
    sun = sim.central
    rel = sim.asteroid_positions[:, :2] - np.array([sun.x, sun.y])
    r = np.hypot(rel[:, 0], rel[:, 1]) / config.AU
    assert np.mean((r > 1.7) & (r < 4.0)) > 0.98


def test_hourly_advance_matches_daily_steps():
    daily, hourly = _run(0, asteroids=True), _run(0, asteroids=True)
    for _ in range(10):
        daily.step()
    for _ in range(240):
        hourly.advance(3600)
    assert hourly.day == daily.day == 10
    for a, b in zip(daily.bodies, hourly.bodies, strict=True):
        assert math.dist((a.x, a.y, a.z), (b.x, b.y, b.z)) < 1.0  # < 1 m Unterschied
    assert np.allclose(daily.asteroid_positions, hourly.asteroid_positions, atol=1.0)


def test_moons_move_smoothly_at_one_hour_per_frame():
    """Io (42,5 h Umlauf) soll pro Stunde nur ~8,5° weiterlaufen – vorher 203°/Frame."""
    sim = _run(0)
    io = by_name(sim.bodies, "Io")
    angles = []
    for _ in range(5):
        angles.append(math.atan2(io.y - io.parent.y, io.x - io.parent.x))
        sim.advance(3600)
    steps = [
        math.degrees(math.remainder(b - a, 2 * math.pi))
        for a, b in zip(angles, angles[1:], strict=False)
    ]
    assert all(8.0 < s < 9.0 for s in steps)


def test_step_counts_days_and_date():
    sim = _run(3)
    assert sim.day == 3
    assert sim.current_jd == JD + 3


def test_create_solar_system_returns_fresh_objects():
    first, second = create_solar_system(JD), create_solar_system(JD)
    assert all(a is not b for a, b in zip(first, second, strict=True))


def test_asteroids_move_smoothly_within_a_day():
    """Asteroiden rechnen nur einen Schritt pro Tag – die Anzeige darf trotzdem nicht springen."""
    sim = _run(0, asteroids=True)
    snapshots = []
    for _ in range(49):
        snapshots.append(sim.asteroid_positions.copy())
        sim.advance(3600)
    hourly_moves = [
        np.linalg.norm(b - a, axis=1) for a, b in zip(snapshots, snapshots[1:], strict=False)
    ]
    per_asteroid = np.array(hourly_moves)  # (48 Stunden, K Asteroiden)
    ratio = per_asteroid.max(axis=0) / per_asteroid.min(axis=0)
    assert np.all(ratio < 1.01)  # jede Stunde praktisch gleich weit
