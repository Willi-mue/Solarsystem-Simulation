import pytest

from solarsystem.i18n import STRINGS, Translator


def test_both_languages_have_the_same_keys():
    assert STRINGS["de"].keys() == STRINGS["en"].keys()


def test_toggle_switches_language():
    tr = Translator("de")
    tr.toggle()
    assert tr.language == "en"
    tr.toggle()
    assert tr.language == "de"


def test_unknown_language_is_rejected():
    with pytest.raises(ValueError):
        Translator("fr")


@pytest.mark.parametrize(
    ("language", "number", "date", "name"),
    [
        ("de", "1.234,57", "7. November 2026", "Erde"),
        ("en", "1,234.57", "November 7, 2026", "Earth"),
    ],
)
def test_formatting(language, number, date, name):
    tr = Translator(language)
    assert tr.number(1234.567, 2) == number
    assert tr.date(2461351.5) == date
    assert tr.name("Earth") == name


def test_mass_and_speed():
    tr = Translator("de")
    assert tr.mass(5.9722e24) == "5,97 × 10²⁴ kg"
    assert tr.speed(1) == "1 Minute/Frame"
    assert tr.speed(15) == "15 Minuten/Frame"
    assert tr.speed(60) == "1 Stunde/Frame"
    assert tr.speed(360) == "6 Stunden/Frame"
    assert tr.speed(1440) == "1 Tag/Frame"
    assert tr.speed(8 * 1440) == "8 Tage/Frame"
    assert Translator("en").speed(5) == "5 minutes/frame"


def test_date_with_time():
    jd = 2461351.5 + 14.5 / 24  # 14:30 UTC
    assert Translator("de").date(jd, with_time=True) == "7. November 2026  ·  14:30 UTC"
    assert Translator("en").date(jd, with_time=True) == "November 7, 2026  ·  14:30 UTC"
