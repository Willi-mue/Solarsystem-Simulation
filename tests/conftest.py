import pytest

from solarsystem.bodies import create_solar_system
from solarsystem.physics import Body

JD = 2461351.5  # 7. November 2026, 0:00 UTC – fester Starttag für reproduzierbare Tests


def by_name(bodies: list[Body], name: str) -> Body:
    return next(b for b in bodies if b.name == name)


@pytest.fixture
def bodies() -> list[Body]:
    return create_solar_system(JD)
