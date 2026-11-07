# TODO – Solarsystem-Simulation

Stand 2026-11-07. Erledigte Punkte sind entfernt. Offene Entscheidungen stehen in `DEV_TODO.md`.

## Genauigkeit

- [ ] Echte Startwinkel für Io, Europa, Ganymed, Kallisto, Titan und Triton
  - Approach: In `bodies.py` stehen bei `MoonData.longitude_j2000` für diese Monde nur Näherungswerte (nur der Erdmond ist real). Mittlere Längen zu J2000 aus den JPL-Satellitenelementen übernehmen (https://ssd.jpl.nasa.gov/sats/elem/) und dabei die Bezugsebene der Elemente (Laplace-Ebene) beachten.
  - Touches: `src/solarsystem/bodies.py`, neuer Test in `tests/test_physics.py`
  - Done when: Ein Test vergleicht die Position der Galileischen Monde zu einem Datum mit JPL-Horizons-Werten (Winkelabweichung < 10°).

- [ ] Bahnneigung der Monde berücksichtigen
  - Approach: `MoonOrbit` in `physics.py` beschreibt nur Kreisbahnen in der Ekliptik (`moon.z = parent.z`). Für Triton (157° zur Ekliptik) und den Erdmond (5,1°) Neigung und Knotenlänge ergänzen und den Kreis in 3D drehen, analog zu `orbits.state_from_elements`.
  - Touches: `src/solarsystem/physics.py`, `src/solarsystem/bodies.py`
  - Done when: Der Erdmond erreicht in einem Test bis zu ±5,1° ekliptikale Breite.
