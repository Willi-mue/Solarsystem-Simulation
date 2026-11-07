"""Texte auf Deutsch und Englisch, inkl. Zahlen- und Datumsformat. Ohne GUI."""

from __future__ import annotations

import math

from .orbits import datetime_from_jd

LANGUAGES = ("de", "en")

STRINGS: dict[str, dict[str, str]] = {
    "de": {
        "window_title": "Sonnensystem",
        "day": "Tag",
        "years": "Jahre",
        "paused": "Pausiert",
        "speed_minute": "{n} Minute/Frame",
        "speed_minutes": "{n} Minuten/Frame",
        "speed_hour": "{n} Stunde/Frame",
        "speed_hours": "{n} Stunden/Frame",
        "speed_day": "{n} Tag/Frame",
        "speed_days": "{n} Tage/Frame",
        "scale_real": "Echte Größen",
        "scale_stylized": "Stilisierte Größen",
        "following": "Folge: {name}",
        "mass": "Masse",
        "radius": "Radius",
        "distance_to": "Abstand zu {name}",
        "orbital_speed": "Bahngeschwindigkeit",
        "au": "AE",
        "help_1": (
            "Leertaste  Pause   ·   +/−  Tempo   ·   Mausrad  Zoom   ·   Ziehen  Verschieben   ·   "
            "Klick  Info   ·   0–9 / F  Folgen   ·   R  Ansicht zurücksetzen"
        ),
        "help_2": (
            "M  Maßstab   ·   A  Asteroiden   ·   T  Spuren   ·   O  Bahnen   ·   L  Namen   ·   "
            "H  Hilfe   ·   F2  English   ·   F11  Vollbild   ·   Esc  Beenden"
        ),
    },
    "en": {
        "window_title": "Solar System",
        "day": "Day",
        "years": "years",
        "paused": "Paused",
        "speed_minute": "{n} minute/frame",
        "speed_minutes": "{n} minutes/frame",
        "speed_hour": "{n} hour/frame",
        "speed_hours": "{n} hours/frame",
        "speed_day": "{n} day/frame",
        "speed_days": "{n} days/frame",
        "scale_real": "True scale",
        "scale_stylized": "Stylized sizes",
        "following": "Following: {name}",
        "mass": "Mass",
        "radius": "Radius",
        "distance_to": "Distance to {name}",
        "orbital_speed": "Orbital speed",
        "au": "AU",
        "help_1": (
            "Space  Pause   ·   +/−  Speed   ·   Scroll  Zoom   ·   Drag  Pan   ·   "
            "Click  Info   ·   0–9 / F  Follow   ·   R  Reset view"
        ),
        "help_2": (
            "M  Scale   ·   A  Asteroids   ·   T  Trails   ·   O  Orbits   ·   L  Labels   ·   "
            "H  Help   ·   F2  Deutsch   ·   F11  Fullscreen   ·   Esc  Quit"
        ),
    },
}

# Körpernamen sind intern englisch; nur abweichende deutsche Namen stehen hier.
NAMES_DE = {
    "Sun": "Sonne",
    "Mercury": "Merkur",
    "Earth": "Erde",
    "Neptune": "Neptun",
    "Moon": "Mond",
    "Ganymede": "Ganymed",
    "Callisto": "Kallisto",
}

MONTHS = {
    "de": (
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ),
    "en": (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ),
}  # fmt: skip

SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


class Translator:
    def __init__(self, language: str = "de") -> None:
        if language not in LANGUAGES:
            raise ValueError(f"Unbekannte Sprache: {language}")
        self.language = language

    def toggle(self) -> None:
        index = LANGUAGES.index(self.language)
        self.language = LANGUAGES[(index + 1) % len(LANGUAGES)]

    def t(self, key: str, **values: object) -> str:
        return STRINGS[self.language][key].format(**values)

    def name(self, body_name: str) -> str:
        return NAMES_DE.get(body_name, body_name) if self.language == "de" else body_name

    def number(self, value: float, decimals: int = 0) -> str:
        """Tausendertrennzeichen und Dezimalzeichen passend zur Sprache."""
        text = f"{value:,.{decimals}f}"
        if self.language == "de":
            text = text.replace(",", "\0").replace(".", ",").replace("\0", ".")
        return text

    def mass(self, kg: float) -> str:
        exponent = math.floor(math.log10(kg))
        mantissa = self.number(kg / 10**exponent, 2)
        return f"{mantissa} × 10{str(exponent).translate(SUPERSCRIPT)} kg"

    def speed(self, minutes_per_frame: int) -> str:
        if minutes_per_frame < 60:
            n, unit = minutes_per_frame, "minute"
        elif minutes_per_frame < 1440:
            n, unit = minutes_per_frame // 60, "hour"
        else:
            n, unit = minutes_per_frame // 1440, "day"
        return self.t(f"speed_{unit}" if n == 1 else f"speed_{unit}s", n=n)

    def date(self, jd: float, with_time: bool = False) -> str:
        """Datum, optional mit Uhrzeit (UTC) – sinnvoll bei langsamen Geschwindigkeiten."""
        d = datetime_from_jd(jd + 1 / 2880)  # auf volle Minuten runden
        month = MONTHS[self.language][d.month - 1]
        text = (
            f"{d.day}. {month} {d.year}" if self.language == "de" else f"{month} {d.day}, {d.year}"
        )
        if with_time:
            text += f"  ·  {d:%H:%M} UTC"
        return text
