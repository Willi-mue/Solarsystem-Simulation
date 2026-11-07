"""Zentrale Konstanten der Simulation (Physik, Darstellung, Fenster)."""

# --- Physik ---------------------------------------------------------------
AU = 149.597870700e9  # Astronomische Einheit in Metern
G = 6.67430e-11  # Gravitationskonstante in m^3 / (kg * s^2)
TIMESTEP = 3600 * 24  # Simulierte Sekunden pro Schritt (1 Tag)
SUBSTEPS = 4  # Teilschritte pro Tag (6 h) -> genauere Bahnen, v. a. Merkur und Halley
# Wählbare Geschwindigkeiten in simulierten Minuten pro Frame (1 min … 64 Tage).
# Die langsamen Stufen sind für die Monde gedacht: Io umrundet Jupiter in 42,5 h,
# bei 5 min/Frame (50 fps) dauert ein Umlauf also ~10 s, bei 1 min/Frame ~51 s.
SPEEDS_MINUTES = (
    1, 5, 15, 30,                         # Minuten
    60, 3 * 60, 6 * 60, 12 * 60,          # Stunden
    1440, 2 * 1440, 4 * 1440, 8 * 1440,   # Tage
    16 * 1440, 32 * 1440, 64 * 1440,
)  # fmt: skip
DEFAULT_SPEED_MINUTES = 1440

ASTEROID_COUNT = 500  # Testteilchen im Hauptgürtel
ASTEROID_SEED = 7  # fester Seed -> immer derselbe Gürtel
# Asteroiden spüren nur Körper ab dieser Masse (Sonne, Jupiter, Saturn) – der Rest
# ist für sie vernachlässigbar und würde die Rechnung ~4× teurer machen.
ASTEROID_PERTURBER_MIN_MASS = 5e26

# --- Darstellung ----------------------------------------------------------
SCALE = 500 / AU  # Pixel pro Meter bei Zoom 1.0 -> 1 AU = 500 px
RADIUS_SCALE = 4  # Faktor für die stilisierten Körperradien
STYLIZED_GROWTH = 0.35  # stilisierte Körper wachsen über Zoom 1 nur mit zoom^x

ZOOM_DEFAULT = 1.0
ZOOM_MIN = 0.01  # ganzes System inkl. Pluto und Halley-Aphel
ZOOM_MAX = 200_000.0  # nah genug, um bei echten Größen den Erdmond zu sehen
ZOOM_STEP = 1.1  # Faktor pro Mausrad-Raste

MIN_BODY_RADIUS_PX = 2.5  # stilisiert: Körper bleiben auch bei kleinem Zoom sichtbar
MIN_REAL_RADIUS_PX = 1.5  # echte Größen: winzige Körper als Punkt anzeigen
PICK_TOLERANCE_PX = 8  # Klick-Toleranz um einen Körper herum
DRAG_THRESHOLD_PX = 4  # ab dieser Mausbewegung zählt ein Klick als Ziehen
STAR_DENSITY = 1 / 4500  # Sterne pro Pixel im Hintergrund
TRAIL_ORBIT_FRACTION = 0.25  # Spurlänge als Anteil eines Umlaufs
TRAIL_MAX_POINTS = 200
TRAIL_FADE_SEGMENTS = 8
ORBIT_SAMPLES = 180  # Punkte pro Bahnellipse
ORBIT_REFRESH_DAYS = 10  # Bahnellipsen alle n Tage neu berechnen

UI_FONT_FAMILY = "Segoe UI"
DEFAULT_LANGUAGE = "de"  # "de" oder "en", umschaltbar mit F2

# --- Fenster --------------------------------------------------------------
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 600
FRAME_INTERVAL_MS = 20  # ein Frame alle 20 ms (50 fps)

WINDOWS_APP_ID = "by_Müller_Willi.Solarsystem"
