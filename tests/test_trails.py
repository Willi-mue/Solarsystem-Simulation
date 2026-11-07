from solarsystem import config
from solarsystem.bodies import create_solar_system
from solarsystem.physics import Simulation
from solarsystem.trails import Trails

from .conftest import JD, by_name


def _run(days: int):
    sim = Simulation(create_solar_system(JD), start_jd=JD)
    trails = Trails(sim.bodies)
    for _ in range(days):
        sim.step()
        trails.record(sim.bodies, sim.day)
    return sim, trails


def test_sun_and_moons_have_no_trail():
    sim, trails = _run(50)
    assert trails.points(by_name(sim.bodies, "Sun")) == []
    assert all(trails.points(m) == [] for m in sim.moons)


def test_trail_length_is_bounded():
    sim, trails = _run(2000)
    for body in sim.bodies:
        assert len(trails.points(body)) <= config.TRAIL_MAX_POINTS
    # Erde: ein Viertel Umlauf ~ 91 Tage, jeder Tag gespeichert
    assert 85 <= len(trails.points(by_name(sim.bodies, "Earth"))) <= 95
    assert trails.points(by_name(sim.bodies, "Halley"))  # Komet hat eine Spur
