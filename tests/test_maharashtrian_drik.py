"""Maharashtrian (Amanta) style against Drik Panchang's iPhone app and Kalnirnay, Pune.

Founder's screenshots, 2026-10-28 (Drik app, Pune, Amanta): month names, Shaka year and
element end times. Drik labels the Chaitradi year "Vikram Samvat 2083" and the Kartikadi year
"Gujarati Samvat" (2082 until 9 Nov, 2083 from 10 Nov 2026); Kalnirnay calls the Kartikadi year
"विक्रम संवत २०८२", which is what this profile returns as vikram_samvat.

The founder's Kalnirnay October 2026 page gives the same end times for 1 Oct: Panchami 12.35,
Rohini 28.26, Siddhi 21.18, Garaja 23.25.

Not compared: the Drik app's sunrise/sunset (06:29 AM / 06:20 PM on 1 Oct) use the Sun's disc
centre without refraction ("Hindu sunrise"), and its moonrise/moonset (10:00 PM / 10:51 AM) the
Moon's upper limb with refraction; the API follows Drik's website defaults (06:25 / 06:23 PM,
10:04 PM / 10:45 AM), verified in tests/reference_six_cities.py. Open question for the founder.
"""

import pytest

from tests.conftest import minutes_apart

PUNE = {"city_id": "1259229", "profile": "maharashtrian-smarta"}

CASES = [
    # date, Amanta month, Purnimanta month, Kartikadi Vikram year, {element: (name, end)}
    (
        "2026-10-01",
        "Bhadrapada",
        "Ashwin",
        2082,
        {
            "tithi": ("Panchami", "2026-10-01T12:35"),
            "nakshatra": ("Rohini", "2026-10-02T04:27"),
            "yoga": ("Siddhi", "2026-10-01T21:18"),
        },
    ),
    ("2026-10-28", "Ashwin", "Kartika", 2082, {"nakshatra": ("Krittika", "2026-10-28T13:26")}),
    (
        "2026-11-09",
        "Ashwin",
        "Kartika",
        2082,
        {"nakshatra": ("Swati", "2026-11-09T07:24"), "moon_sign": ("Tula", "2026-11-10T02:48")},
    ),
    ("2026-11-10", "Kartika", "Kartika", 2083, {"karana": ("Bava", "2026-11-10T14:00")}),
]


@pytest.mark.parametrize(("day", "amanta", "purnimanta", "vikram", "ends"), CASES)
def test_matches_drik_app(daily, day, amanta, purnimanta, vikram, ends):
    body = daily(day, **PUNE)
    assert body["masa"]["amanta"]["name"] == amanta
    assert body["masa"]["purnimanta"]["name"] == purnimanta
    assert (body["year"]["shaka_samvat"], body["year"]["shaka_samvatsara"]["name"]) == (
        1948,
        "Parabhava",
    )
    assert body["year"]["vikram_samvat"] == vikram
    for element, (name, end) in ends.items():
        first = body[element]["spans"][0]
        assert first["name"] == name, element
        assert minutes_apart(first["end"], end) <= 1, element


def test_second_karanas_match_drik_app(daily):
    # Drik: 1 Oct Garaja upto 11:24 PM; 10 Nov Balava upto 02:53 AM, Nov 11.
    oct1 = [s for s in daily("2026-10-01", **PUNE)["karana"]["spans"] if s["name"] == "Garaja"]
    assert minutes_apart(oct1[0]["end"], "2026-10-01T23:24") <= 1
    nov10 = [s for s in daily("2026-11-10", **PUNE)["karana"]["spans"] if s["name"] == "Balava"]
    assert minutes_apart(nov10[0]["end"], "2026-11-11T02:53") <= 1


def test_amavasya_name_matches_drik_app(daily):
    # Drik, 9 Nov 2026: "Ashwina Amavasya" (the North calls it Kartika Amavasya).
    names = [o["name"] for o in daily("2026-11-09", **PUNE)["observances"]]
    assert "Ashwin Amavasya" in names
