"""Kalnirnay (Marathi) October 2026 against the API, Mumbai (Kalnirnay's reference place).

Founder's photos, 2026-10-28: the Panchang table (end times of Tithi, Nakshatra, Yoga, Karana,
"hours.minutes" counted past midnight up to the next sunrise) and the wall-calendar page
(sunrise, sunset, Moon sign, festivals).

Findings: all 128 end times within 2 minutes (the API is 0-2 minutes later, the known Lahiri
variant difference). Sunrise is 2-3 minutes earlier and sunset 1-2 minutes later in the API:
Kalnirnay's rise/set fit no standard rule exactly (best fit: Sun's centre at -0.36 degrees).
Sankashti moonrise 29 Oct: Kalnirnay 8:47 PM, API 9:00 PM (open, see CALCULATIONS.md).
"""

from datetime import datetime, timedelta

import pytest

MUMBAI = {"city_id": "1275339", "profile": "maharashtrian-smarta"}

# day: (element, hh.mm) in table order; Kalnirnay's names are in the comments.
TABLE = {
    1: "tithi 12.35|nakshatra 28.26|yoga 21.18|karana 23.25",  # Panchami, Rohini, Siddhi, Garaja
    2: "tithi 10.15|nakshatra 26.54|yoga 18.17|karana 21.06",
    3: "tithi 07.59|tithi 29.51|nakshatra 25.29|yoga 15.21|karana 18.54",
    4: "tithi 27.53|nakshatra 24.13|yoga 12.31|karana 16.51",
    5: "tithi 26.07|nakshatra 23.08|yoga 09.50|karana 14.58",
    6: "tithi 24.34|nakshatra 22.17|yoga 07.19|yoga 28.59|karana 13.19",
    7: "tithi 23.16|nakshatra 21.40|yoga 26.51|karana 11.53",
    8: "tithi 22.15|nakshatra 21.19|yoga 24.57|karana 10.43",
    9: "tithi 21.35|nakshatra 21.19|yoga 23.20|karana 09.52",
    10: "tithi 21.19|nakshatra 21.42|yoga 22.01|karana 09.24",  # Amavasya ends 9:19 PM
    11: "tithi 21.30|nakshatra 22.32|yoga 21.04|karana 09.21",
    12: "tithi 22.12|nakshatra 23.51|yoga 20.31|karana 09.47",
    13: "tithi 23.27|nakshatra 25.42|yoga 20.23|karana 10.46",
    14: "tithi 25.12|nakshatra 28.02|yoga 20.38|karana 12.16",
    15: "tithi 27.24|yoga 21.14|karana 14.15",
    16: "tithi 29.54|nakshatra 06.47|yoga 22.04|karana 16.37",
    17: "nakshatra 09.46|yoga 23.01|karana 19.10",
    18: "tithi 08.27|nakshatra 12.47|yoga 23.54|karana 21.41",
    19: "tithi 10.51|nakshatra 15.37|yoga 24.33|karana 23.54",
    20: "tithi 12.49|nakshatra 18.00|yoga 24.48|karana 25.35",
    21: "tithi 14.11|nakshatra 19.46|yoga 24.32|karana 26.35",
    22: "tithi 14.47|nakshatra 20.48|yoga 23.38|karana 26.47",
    23: "tithi 14.35|nakshatra 21.02|yoga 22.07|karana 26.11",
    24: "tithi 13.36|nakshatra 20.31|yoga 20.00|karana 24.51",
    25: "tithi 11.56|nakshatra 19.21|yoga 17.21|karana 22.52",
    26: "tithi 09.41|nakshatra 17.41|yoga 14.16|karana 20.24",  # Purnima ends 9:41 AM
    27: "tithi 07.01|tithi 28.06|nakshatra 15.39|yoga 10.52|karana 17.35",
    28: "tithi 25.06|nakshatra 13.26|yoga 07.17|yoga 27.40|karana 14.37",
    29: "tithi 22.10|nakshatra 11.11|yoga 24.05|karana 11.37",
    30: "tithi 19.24|nakshatra 09.03|yoga 20.41|karana 08.45|karana 30.08",
    31: "tithi 16.57|nakshatra 07.11|nakshatra 29.39|yoga 17.31|karana 27.51",
}

# day: (sunrise, sunset) from the wall calendar
SUN = {
    1: ("06:31", "18:25"), 2: ("06:32", "18:24"), 3: ("06:32", "18:24"), 4: ("06:32", "18:23"),
    5: ("06:32", "18:22"), 6: ("06:32", "18:21"), 7: ("06:33", "18:20"), 8: ("06:33", "18:19"),
    9: ("06:33", "18:19"), 10: ("06:33", "18:18"), 11: ("06:34", "18:17"), 12: ("06:34", "18:16"),
    13: ("06:34", "18:15"), 14: ("06:34", "18:15"), 15: ("06:35", "18:14"), 16: ("06:35", "18:13"),
    17: ("06:35", "18:13"), 18: ("06:36", "18:12"), 19: ("06:36", "18:11"), 20: ("06:36", "18:10"),
    21: ("06:37", "18:10"), 22: ("06:37", "18:09"), 23: ("06:37", "18:08"), 24: ("06:38", "18:08"),
    25: ("06:38", "18:07"), 26: ("06:38", "18:07"), 27: ("06:39", "18:06"), 28: ("06:39", "18:05"),
    29: ("06:40", "18:05"), 30: ("06:40", "18:04"), 31: ("06:40", "18:04"),
}  # fmt: skip


def _minute(iso: str) -> datetime:
    t = datetime.fromisoformat(iso).replace(tzinfo=None)
    return t.replace(second=0, microsecond=0) + timedelta(minutes=t.second >= 30)


@pytest.mark.parametrize("day", sorted(TABLE))
def test_end_times_within_two_minutes(daily, day):
    body = daily(f"2026-10-{day:02d}", **MUMBAI)
    midnight = datetime(2026, 10, day)
    for item in TABLE[day].split("|"):
        element, hhmm = item.split()
        hours, minutes = map(int, hhmm.split("."))
        expected = midnight + timedelta(hours=hours, minutes=minutes)
        ends = [_minute(s["end"]) for s in body[element]["spans"] if s.get("end")]
        nearest = min(abs((e - expected).total_seconds()) / 60 for e in ends)
        assert nearest <= 2, f"Oct {day} {element} {hhmm}"


@pytest.mark.parametrize("day", sorted(SUN))
def test_sunrise_and_sunset_within_three_minutes(daily, day):
    body = daily(f"2026-10-{day:02d}", **MUMBAI)
    for event, hhmm in zip(("sunrise", "sunset"), SUN[day], strict=True):
        hours, minutes = map(int, hhmm.split(":"))
        actual = _minute(body["sun"][event]["time"])
        assert abs(actual.hour * 60 + actual.minute - hours * 60 - minutes) <= 3, (day, event)


def test_festival_dates_match_kalnirnay(client):
    body = client.get("/v1/festivals", params={"year": 2026, **MUMBAI}).json()
    dates = {f["festival_id"]: f["date"] for f in body["festivals"] if f["date"][:7] == "2026-10"}
    # Kalnirnay October 2026 (names as printed there)
    assert dates["indira-ekadashi"] == "2026-10-06"  # इंदिरा एकादशी
    assert dates["sharad-navratri"] == "2026-10-11"  # घटस्थापना
    assert dates["durga-ashtami"] == "2026-10-19"  # दुर्गाष्टमी
    assert dates["dussehra"] == "2026-10-20"  # दसरा
    assert dates["sharad-purnima"] == "2026-10-25"  # कोजागरी पौर्णिमा
    assert dates["sankashti-chaturthi"] == "2026-10-29"  # संकष्ट चतुर्थी
    assert dates["krishna-pradosh"] == dates["masik-shivaratri"] == "2026-10-08"  # प्रदोष, शिवरात्री
    assert dates["sarva-pitru-amavasya"] == "2026-10-10"  # सर्वपित्री दर्श अमावास्या
    assert dates["vinayaka-chaturthi"] == "2026-10-14"  # विनायक चतुर्थी
    assert dates["maha-navami"] == "2026-10-20"  # महानवमी
    assert dates["papankusha-ekadashi"] == "2026-10-22"  # पाशांकुशा एकादशी
    assert dates["shukla-pradosh"] == "2026-10-23"  # प्रदोष
    assert dates["karwa-chauth"] == "2026-10-29"  # करक चतुर्थी
