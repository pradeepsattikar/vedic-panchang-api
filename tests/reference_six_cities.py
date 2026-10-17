# ruff: noqa: E501  (reference table: one Drik reading per line)
"""Drik Panchang reference values for the six BR-015 cities (EN-19/EN-20).

Read from drikpanchang.com day pages (same GeoNames IDs; London by coordinates) on 2026-10-17.
Times are local, as Drik shows them (rounded to the minute). Short times are on the case's date;
times on another day carry their full date. None = Drik shows "No Moonrise"/"No Moonset".
"full" = Drik shows the element lasting "upto Full Night" (beyond the next sunrise).

Categories covered (BR-015): normal days, festival dates (Diwali 2026-11-08, Dussehra week),
DST transitions (2026-11-01 North America, 2026-10-25 UK; Vancouver stays UTC-7), midnight
boundaries (Tithi/Moon events after midnight), Tithi and Nakshatra transitions, no-moonrise days
and the 2028 leap day.
"""

TORONTO = {"city_id": "6167865"}
VANCOUVER = {"city_id": "6173331"}
NEW_YORK = {"city_id": "5128581"}
LONDON = {"lat": 51.50853, "lon": -0.12574, "tz": "Europe/London"}
MUMBAI = {"city_id": "1275339"}
PUNE = {"city_id": "1259229"}


def case(place, day, sun, moon, tithi, nakshatra, rahu, yama, gulika, abhijit, brahma, why):
    return {
        "place": place,
        "date": day,
        "why": why,
        "sunrise": sun[0],
        "sunset": sun[1],
        "moonrise": moon[0],
        "moonset": moon[1],
        "tithi": tithi,
        "nakshatra": nakshatra,
        "timings": {
            "rahu_kalam": rahu,
            "yamaganda": yama,
            "gulika_kalam": gulika,
            "abhijit_muhurta": abhijit,
            "brahma_muhurta": brahma,
        },
    }


CASES = [
    # ── Toronto ──
    case(TORONTO, "2026-10-17", ("07:35", "18:31"), ("14:36", "23:01"), ("Saptami", "22:57"),
         ("Purva Ashadha", "2026-10-18T03:19"), ("10:19", "11:41"), ("14:25", "15:47"),
         ("07:35", "08:57"), ("12:41", "13:25"), ("05:50", "06:42"), "normal day"),
    case(TORONTO, "2026-10-25", ("07:45", "18:18"), ("17:47", None), ("Purnima", "2026-10-26T00:11"),
         ("Revati", "09:52"), ("16:59", "18:18"), ("13:01", "14:21"), ("15:40", "16:59"),
         ("12:40", "13:23"), ("05:57", "06:51"), "Tithi ends after midnight; no moonset"),
    case(TORONTO, "2026-11-01", ("06:54", "17:08"), ("23:35", "13:32"), ("Ashtami", "2026-11-02T02:40"),
         ("Pushya", "18:00"), ("15:51", "17:08"), ("12:01", "13:18"), ("14:35", "15:51"),
         ("11:40", "12:21"), ("05:04", "05:59"), "DST ends (fall back)"),
    case(TORONTO, "2026-11-08", ("07:03", "16:59"), (None, "16:09"), ("Amavasya", "2026-11-09T02:01"),
         ("Swati", "20:54"), ("15:45", "16:59"), ("12:01", "13:16"), ("14:30", "15:45"),
         ("11:41", "12:21"), ("05:10", "06:07"), "Diwali; no moonrise"),
    case(TORONTO, "2028-02-29", ("06:55", "18:06"), ("08:17", "22:40"), ("Chaturthi", "14:12"),
         ("Ashwini", "full"), ("15:18", "16:42"), ("09:43", "11:07"), ("12:30", "13:54"),
         ("12:08", "12:53"), ("05:12", "06:04"), "leap day"),
    # ── Vancouver (permanent UTC-7 since March 2026) ──
    case(VANCOUVER, "2026-10-17", ("07:37", "18:18"), ("15:04", "22:36"), ("Saptami", "19:57"),
         ("Purva Ashadha", "2026-10-18T00:19"), ("10:17", "11:37"), ("14:18", "15:38"),
         ("07:37", "08:57"), ("12:36", "13:19"), ("05:51", "06:44"), "normal day"),
    case(VANCOUVER, "2026-10-19", ("07:40", "18:14"), ("15:54", "2026-10-20T00:58"),
         ("Navami", "2026-10-20T00:20"), ("Shravana", "2026-10-20T05:32"), ("08:59", "10:19"),
         ("11:38", "12:57"), ("14:16", "15:36"), ("12:36", "13:18"), ("05:53", "06:46"),
         "Tithi and moonset after midnight"),
    case(VANCOUVER, "2026-11-01", ("08:01", "17:51"), ("2026-11-02T00:23", "14:48"),
         ("Ashtami", "2026-11-02T00:40"), ("Pushya", "16:00"), ("16:37", "17:51"),
         ("12:56", "14:09"), ("15:23", "16:37"), ("12:36", "13:15"), ("06:08", "07:04"),
         "no clock change (BC permanent daylight time)"),
    case(VANCOUVER, "2026-11-08", ("08:12", "17:40"), (None, "16:47"), ("Amavasya", "2026-11-09T00:01"),
         ("Swati", "18:54"), ("16:29", "17:40"), ("12:56", "14:07"), ("15:18", "16:29"),
         ("12:37", "13:15"), ("06:16", "07:14"), "Diwali; no moonrise"),
    # ── New York ──
    case(NEW_YORK, "2026-10-17", ("07:09", "18:13"), ("14:01", "22:50"), ("Saptami", "22:57"),
         ("Purva Ashadha", "2026-10-18T03:19"), ("09:55", "11:18"), ("14:04", "15:27"),
         ("07:09", "08:32"), ("12:19", "13:03"), ("05:26", "06:18"), "normal day"),
    case(NEW_YORK, "2026-11-01", ("06:26", "16:52"), ("23:19", "13:02"), ("Ashtami", "2026-11-02T02:40"),
         ("Pushya", "18:00"), ("15:34", "16:52"), ("11:39", "12:58"), ("14:16", "15:34"),
         ("11:18", "12:00"), ("04:38", "05:32"), "DST ends (fall back)"),
    case(NEW_YORK, "2026-11-03", ("06:29", "16:50"), ("2026-11-04T01:41", "13:58"),
         ("Dashami", "2026-11-04T00:33"), ("Magha", "16:56"), ("14:15", "15:32"), ("09:04", "10:22"),
         ("11:39", "12:57"), ("11:19", "12:00"), ("04:40", "05:34"), "Tithi and moonrise after midnight"),
    case(NEW_YORK, "2026-11-08", ("06:35", "16:44"), (None, "15:56"), ("Amavasya", "2026-11-09T02:01"),
         ("Swati", "20:54"), ("15:28", "16:44"), ("11:39", "12:56"), ("14:12", "15:28"),
         ("11:19", "12:00"), ("04:44", "05:39"), "Diwali; no moonrise"),
    # ── London ──
    case(LONDON, "2026-10-17", ("07:28", "18:03"), ("14:55", "21:46"), ("Saptami", "2026-10-18T03:57"),
         ("Purva Ashadha", "full"), ("10:07", "11:26"), ("14:05", "15:24"), ("07:28", "08:47"),
         ("12:24", "13:07"), ("05:41", "06:34"), "normal day"),
    case(LONDON, "2026-10-25", ("06:42", "16:47"), ("16:07", None), ("Purnima", "2026-10-26T04:11"),
         ("Revati", "13:52"), ("15:31", "16:47"), ("11:44", "13:00"), ("14:15", "15:31"),
         ("11:24", "12:04"), ("04:51", "05:46"), "BST ends (fall back); no moonset"),
    case(LONDON, "2026-11-08", ("07:06", "16:22"), (None, "15:19"), ("Amavasya", "2026-11-09T07:01"),
         ("Swati", "2026-11-09T01:54"), ("15:12", "16:22"), ("11:44", "12:53"), ("14:03", "15:12"),
         ("11:25", "12:02"), ("05:08", "06:07"), "Diwali; no moonrise"),
    case(LONDON, "2026-11-17", ("07:22", "16:09"), ("13:19", "23:23"), ("Ashtami", "2026-11-18T00:34"),
         ("Dhanishtha", "23:04"), ("13:57", "15:03"), ("09:33", "10:39"), ("11:45", "12:51"),
         ("11:28", "12:03"), ("05:20", "06:21"), "Tithi ends after midnight"),
    # ── Mumbai ──
    case(MUMBAI, "2026-10-17", ("06:33", "18:14"), ("12:20", "23:13"), ("Saptami", "full"),
         ("Mula", "09:47"), ("09:28", "10:56"), ("13:51", "15:19"), ("06:33", "08:01"),
         ("12:00", "12:47"), ("04:55", "05:44"), "normal day; Tithi lasts past next sunrise"),
    case(MUMBAI, "2026-11-08", ("06:42", "18:02"), ("2026-11-09T06:39", "17:09"), ("Chaturdashi", "11:27"),
         ("Swati", "full"), ("16:37", "18:02"), ("12:22", "13:47"), ("15:12", "16:37"),
         ("11:59", "12:45"), ("05:01", "05:51"), "Diwali; moonrise just before next sunrise"),
    case(MUMBAI, "2026-11-09", ("06:43", "18:02"), (None, "17:50"), ("Amavasya", "12:31"),
         ("Swati", "07:24"), ("08:07", "09:32"), ("10:57", "12:22"), ("13:47", "15:12"),
         ("12:00", "12:45"), ("05:01", "05:52"), "no moonrise"),
    case(MUMBAI, "2026-11-23", ("06:50", "17:59"), ("16:47", "2026-11-24T06:15"), ("Chaturdashi", "23:42"),
         ("Bharani", "2026-11-24T02:02"), ("08:14", "09:38"), ("11:01", "12:25"), ("13:48", "15:12"),
         ("12:02", "12:47"), ("05:08", "05:59"), "Tithi ends near midnight"),
    case(MUMBAI, "2028-02-29", ("06:58", "18:44"), ("08:59", "21:54"), ("Chaturthi", "2028-03-01T00:42"),
         ("Revati", "15:58"), ("15:47", "17:16"), ("09:55", "11:23"), ("12:51", "14:19"),
         ("12:27", "13:15"), ("05:20", "06:09"), "leap day; Tithi ends after midnight"),
    # ── Pune ──
    case(PUNE, "2026-10-17", ("06:29", "18:11"), ("12:14", "23:11"), ("Saptami", "full"),
         ("Mula", "09:47"), ("09:24", "10:52"), ("13:48", "15:15"), ("06:29", "07:57"),
         ("11:56", "12:43"), ("04:51", "05:40"), "normal day"),
    case(PUNE, "2026-11-08", ("06:37", "17:59"), ("2026-11-09T06:34", "17:06"), ("Chaturdashi", "11:27"),
         ("Swati", "full"), ("16:34", "17:59"), ("12:18", "13:43"), ("15:09", "16:34"),
         ("11:55", "12:41"), ("04:56", "05:47"), "Diwali"),
    case(PUNE, "2026-11-09", ("06:38", "17:59"), (None, "17:47"), ("Amavasya", "12:31"),
         ("Swati", "07:24"), ("08:03", "09:28"), ("10:53", "12:18"), ("13:43", "15:08"),
         ("11:56", "12:41"), ("04:57", "05:47"), "no moonrise"),
    case(PUNE, "2026-11-30", ("06:50", "17:57"), ("2026-12-01T00:04", "12:02"),
         ("Saptami", "2026-12-01T00:11"), ("Ashlesha", "09:42"), ("08:13", "09:37"), ("11:00", "12:23"),
         ("13:47", "15:10"), ("12:01", "12:45"), ("05:07", "05:58"), "Tithi and moonrise after midnight"),
]  # fmt: skip
