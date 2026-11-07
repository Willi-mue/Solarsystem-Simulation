"""Gravitationsphysik (3D, numpy). Reine Logik ohne GUI-Abhängigkeiten."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import config
from .orbits import J2000


@dataclass(frozen=True)
class MoonOrbit:
    """Kreisbahn eines Mondes um seinen Planeten („auf Schienen“).

    Monde werden nicht per N-Körper-Rechnung integriert: Io umläuft Jupiter in
    1,8 Tagen, das bräuchte Zeitschritte von Minuten. Stattdessen folgt der Mond
    analytisch seinem Planeten – exakt und bei jeder Geschwindigkeit stabil.
    """

    distance: float  # m
    period: float  # s, negativ = rückläufig (Triton)
    phase: float  # rad, Winkel zum Simulationsstart


@dataclass(eq=False)
class Body:
    """Ein Himmelskörper (Stern, Planet, Zwergplanet, Mond, Komet)."""

    name: str
    x: float  # Position in Metern (Ekliptik, Schwerpunktsystem)
    y: float
    radius: float  # stilisierter Darstellungsradius
    color: tuple[int, int, int]
    mass: float  # in kg
    x_vel: float = 0.0  # Geschwindigkeit in m/s
    y_vel: float = 0.0
    has_rings: bool = False  # nur für die Darstellung
    z: float = 0.0
    z_vel: float = 0.0
    real_radius: float = 0.0  # echter Radius in Metern
    parent: Body | None = None  # bei Monden: der Planet
    orbit: MoonOrbit | None = None  # bei Monden: Bahn um den Planeten
    moon_rank: int = 0  # 0 = innerster Mond des Planeten


def move_to_center_of_mass_frame(bodies: list[Body]) -> None:
    """Gesamtimpuls auf null und Schwerpunkt in den Ursprung setzen.

    Ohne das driftet das ganze System langsam aus dem Bild.
    """
    total = sum(b.mass for b in bodies)
    for pos, vel in (("x", "x_vel"), ("y", "y_vel"), ("z", "z_vel")):
        center = sum(b.mass * getattr(b, pos) for b in bodies) / total
        drift = sum(b.mass * getattr(b, vel) for b in bodies) / total
        for b in bodies:
            setattr(b, pos, getattr(b, pos) - center)
            setattr(b, vel, getattr(b, vel) - drift)


class Simulation:
    """N-Körper-Simulation mit dem Velocity-Verlet-Verfahren.

    - Massive Körper (Sonne, Planeten, Komet) ziehen sich gegenseitig an.
    - Asteroiden sind Testteilchen: Sie spüren die Gravitation von Sonne, Jupiter
      und Saturn, üben selbst aber keine aus. Kosten wachsen nur linear.
    - Monde folgen analytisch ihrem Planeten (siehe `MoonOrbit`).

    Velocity Verlet ist symplektisch: Die Energie bleibt über Jahrhunderte stabil.
    """

    def __init__(
        self,
        bodies: list[Body],
        asteroids: tuple[np.ndarray, np.ndarray] | None = None,
        timestep: float = config.TIMESTEP,
        substeps: int = config.SUBSTEPS,
        start_jd: float = J2000,
    ) -> None:
        self.bodies = bodies
        self.massive = [b for b in bodies if b.orbit is None]
        self.moons = [b for b in bodies if b.orbit is not None]
        self.central = max(self.massive, key=lambda b: b.mass)
        self.timestep = timestep
        self.substeps = substeps
        self.dt = timestep / substeps
        self.start_jd = start_jd
        self.time = 0.0  # durchgerechnete Sekunden seit Start (Vielfaches von dt)
        self._pending = 0.0  # angefangener Teilschritt (0 <= _pending < dt)

        self.n_massive = len(self.massive)
        self.pos = np.array([[b.x, b.y, b.z] for b in self.massive], dtype=float)
        self.vel = np.array([[b.x_vel, b.y_vel, b.z_vel] for b in self.massive], dtype=float)
        self.gm = config.G * np.array([b.mass for b in self.massive], dtype=float)
        # Selbstwechselwirkung ausschließen: Abstand eines Körpers zu sich = ∞
        self._self_distance = np.zeros((self.n_massive, self.n_massive))
        np.fill_diagonal(self._self_distance, np.inf)
        self._acc = self._massive_accelerations()

        # Asteroiden: Testteilchen, gestört nur von Sonne, Jupiter, Saturn
        empty = np.zeros((0, 3))
        ast_pos, ast_vel = asteroids if asteroids is not None else (empty, empty)
        self.ast_pos = np.array(ast_pos, dtype=float).reshape(-1, 3)
        self.ast_vel = np.array(ast_vel, dtype=float).reshape(-1, 3)
        self._perturbers = np.array(
            [i for i, b in enumerate(self.massive) if b.mass >= config.ASTEROID_PERTURBER_MIN_MASS]
        )
        self._perturber_gm = self.gm[self._perturbers]
        self._ast_acc = self._asteroid_accelerations()

        self._sync_bodies()

    # ---------------------------------------------------------------- state
    @property
    def elapsed(self) -> float:
        """Simulierte Sekunden seit Start, inkl. angefangenem Teilschritt."""
        return self.time + self._pending

    @property
    def day(self) -> int:
        return int(self.elapsed // 86400)

    @property
    def current_jd(self) -> float:
        return self.start_jd + self.elapsed / 86400

    @property
    def asteroid_positions(self) -> np.ndarray:
        """Asteroiden-Positionen zum aktuellen Zeitpunkt (für die Anzeige).

        Asteroiden machen einen Verlet-Schritt pro Tag; ihre Position steht
        tagsüber schon am Tagesende. Dazwischen wird linear zurückgerechnet.
        """
        day = self.timestep
        if self.time % day:  # mitten im Tag: Drift ist schon erfolgt
            day_end = (self.time // day + 1) * day
            return self.ast_pos - (day_end - self.elapsed) * self.ast_vel
        if self._pending:
            return self.ast_pos + self._pending * self.ast_vel
        return self.ast_pos

    # -------------------------------------------------------------- physics
    def _massive_accelerations(self) -> np.ndarray:
        """Massive Körper ziehen sich gegenseitig an (jeder gegen jeden, numpy)."""
        diff = self.pos[None, :, :] - self.pos[:, None, :]  # (M, M, 3)
        dist_sq = np.einsum("ijk,ijk->ij", diff, diff) + self._self_distance
        weight = self.gm[None, :] / (dist_sq * np.sqrt(dist_sq))
        return np.einsum("ij,ijk->ik", weight, diff)

    def _asteroid_accelerations(self) -> np.ndarray:
        if not len(self.ast_pos):
            return self.ast_pos.copy()
        sources = self.pos[self._perturbers]
        diff = sources[None, :, :] - self.ast_pos[:, None, :]  # (K, S, 3)
        dist_sq = np.einsum("ijk,ijk->ij", diff, diff)
        weight = self._perturber_gm[None, :] / (dist_sq * np.sqrt(dist_sq))
        return np.einsum("ij,ijk->ik", weight, diff)

    def _substep(self) -> None:
        """Ein Velocity-Verlet-Schritt (Kick-Drift-Kick) der Länge dt.

        Massive Körper machen jeden Teilschritt (6 h). Asteroiden machen einen
        Schritt pro Tag – bei Umlaufzeiten von 3–6 Jahren genau genug und 4×
        billiger: Kick + Drift am Tagesanfang, Kick am Tagesende.
        """
        index = round(self.time / self.dt) % self.substeps
        day_half = 0.5 * self.timestep
        if index == 0:
            self.ast_vel += day_half * self._ast_acc
            self.ast_pos += self.timestep * self.ast_vel

        half = 0.5 * self.dt
        self.vel += half * self._acc
        self.pos += self.dt * self.vel
        self._acc = self._massive_accelerations()
        self.vel += half * self._acc
        self.time += self.dt

        if index == self.substeps - 1:
            self._ast_acc = self._asteroid_accelerations()
            self.ast_vel += day_half * self._ast_acc

    def advance(self, seconds: float) -> None:
        """Um beliebig viele Sekunden vorrücken, auch weniger als ein Teilschritt.

        Gerechnet wird immer in ganzen Teilschritten (dt = 6 h). Ein angefangener
        Rest wird nur für die Anzeige linear fortgeschrieben – so laufen Monde
        auch bei 1 Stunde pro Frame flüssig, ohne die Physik ungenauer zu machen.
        """
        self._pending += seconds
        while self._pending >= self.dt - 1e-6:
            self._substep()
            self._pending = max(0.0, self._pending - self.dt)
        self._sync_bodies()

    def step(self) -> None:
        """Genau einen simulierten Tag vorrücken."""
        self.advance(self.timestep)

    def _sync_bodies(self) -> None:
        """Zustand aus den Arrays in die Body-Objekte übertragen (für Anzeige/Trails)."""
        pos = self.pos + self._pending * self.vel if self._pending else self.pos
        positions = pos.tolist()
        velocities = self.vel.tolist()
        for body, (x, y, z), (vx, vy, vz) in zip(self.massive, positions, velocities, strict=True):
            body.x, body.y, body.z = x, y, z
            body.x_vel, body.y_vel, body.z_vel = vx, vy, vz
        for moon in self.moons:
            orbit, parent = moon.orbit, moon.parent
            omega = 2 * math.pi / orbit.period
            angle = orbit.phase + omega * self.elapsed
            c, s = math.cos(angle), math.sin(angle)
            moon.x = parent.x + orbit.distance * c
            moon.y = parent.y + orbit.distance * s
            moon.z = parent.z
            moon.x_vel = parent.x_vel - orbit.distance * omega * s
            moon.y_vel = parent.y_vel + orbit.distance * omega * c
            moon.z_vel = parent.z_vel

    def total_energy(self) -> float:
        """Kinetische + potentielle Energie der massiven Körper (Genauigkeitsprüfung)."""
        mass = self.gm / config.G
        kinetic = 0.5 * float(np.sum(mass * np.einsum("ij,ij->i", self.vel, self.vel)))
        diff = self.pos[:, None, :] - self.pos[None, :, :]
        dist = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))
        iu = np.triu_indices(self.n_massive, k=1)
        potential = -config.G * float(np.sum(mass[iu[0]] * mass[iu[1]] / dist[iu]))
        return kinetic + potential
