"""Lunar month (Masa) naming in Amanta and Purnimanta systems, including Adhika months.

Expected values follow the published 2026 calendar: Adhika Jyeshtha 17 May - 15 Jun 2026;
Sarva Pitru Amavasya (Oct 10) and Diwali (Nov 8) fall on Ashwin / Kartika Amavasya.
"""

import pytest

DELHI = {"lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata", "alt": 216}


@pytest.mark.parametrize(
    ("day", "amanta", "purnimanta"),
    [
        ("2026-04-02", "chaitra", "chaitra"),  # Chaitra Purnima eve: Shukla, systems agree
        ("2026-05-10", "vaishakha", "adhika-jyeshtha"),
        ("2026-05-20", "adhika-jyeshtha", "adhika-jyeshtha"),
        ("2026-06-10", "adhika-jyeshtha", "jyeshtha"),
        ("2026-06-20", "jyeshtha", "jyeshtha"),
        ("2026-10-10", "bhadrapada", "ashwin"),  # Sarva Pitru Amavasya
        ("2026-10-12", "ashwin", "ashwin"),  # Sharad Navratri, Shukla paksha
        ("2026-11-08", "ashwin", "kartika"),  # Diwali
    ],
)
def test_masa(daily, day, amanta, purnimanta):
    masa = daily(day, **DELHI)["masa"]
    assert masa["amanta"]["id"] == amanta
    assert masa["purnimanta"]["id"] == purnimanta


def test_adhika_flag(daily):
    masa = daily("2026-05-20", **DELHI)["masa"]["amanta"]
    assert masa == {"number": 3, "id": "adhika-jyeshtha", "name": "Jyeshtha", "is_adhika": True}
