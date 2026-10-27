# Vedic Panchang API

Open-source, deterministic Vedic Panchang calculations over HTTP, built on the
[Swiss Ephemeris](https://www.astro.com/swisseph/).

For any date and any place on Earth it returns Tithi, Paksha, Nakshatra, Yoga, Karana,
Masa (Amanta and Purnimanta lunar month, with Adhika months),
Vara, sunrise/sunset, moonrise/moonset, Rahu Kalam, Yamaganda, Gulika Kalam, Abhijit
Muhurta and Brahma Muhurta, each with exact start and end times.

**Principles**

- **Calculated, never guessed.** Every value comes from an astronomical calculation. If
  something cannot be calculated (e.g. no sunrise during polar night), the API says so
  explicitly. It never returns `00:00`, blanks or another city's data.
- **Verified.** Results are checked against [Drik Panchang](https://www.drikpanchang.com)
  for reference cities: all timings agree within 1 minute (see `tests/`).
- **Traceable.** Every response states the engine version, timezone-data version,
  calculation profile and rule version that produced it.
- **Tradition as data.** Conventions that differ between traditions live in versioned
  profiles (`src/vedic_panchang/rules/data/profiles.toml`), not in code.

## Quick start

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run uvicorn vedic_panchang.main:app --reload
```

Open http://localhost:8000/docs for interactive API documentation.

With Docker:

```bash
docker build -t vedic-panchang-api .
docker run -p 8000:8000 vedic-panchang-api
```

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /v1/panchang/daily?city_id=6167865&date=2026-10-10` | Daily Panchang for a catalogue city |
| `GET /v1/panchang/daily?lat=19.07&lon=72.88&tz=Asia/Kolkata&date=2026-10-10` | Daily Panchang for any coordinates (`alt` optional, metres) |
| `GET /v1/panchang/month?city_id=6167865&year=2026&month=11` | One compact summary per day (Tithi/Nakshatra at sunrise, sunrise/sunset, Masa, festivals) for calendar views |
| `GET /v1/festivals?city_id=6167865&year=2026` | Festivals and observances in a year, with local dates (`category=major` to filter) |
| `GET /v1/festivals/diwali?city_id=6167865&year=2026` | Occurrences of one festival |
| `GET /v1/cities?q=toronto&country=CA` | Search the city catalogue (case- and accent-insensitive) |
| `GET /v1/cities/nearest?lat=43.65&lon=-79.38` | Nearest catalogue city to a point |
| `GET /v1/cities/{city_id}` | One city |
| `GET /v1/meta` | Versions, profiles, supported date range, catalogue info |
| `GET /health` | Liveness check |

Optional on daily, month, festival and muhurta requests: `profile` — `north-indian-smarta`
(default; Purnimanta month names) or `maharashtrian-smarta` (Amanta month names). If
`date`/`year` is omitted, the API uses today's date at the requested location. Daily
responses list that day's festivals under `observances`.

### Festivals

Festival rules are data: `src/vedic_panchang/rules/data/festivals/<set>.toml`. A lunar
festival falls on the local day on which its Tithi prevails during a given part of the day
(`kala`: sunrise, purvahna, madhyahna, aparahna, pradosh, nishita, moonrise, ...), with a
tie-break when it prevails on two days and Bhadra avoidance where tradition requires it
(e.g. Raksha Bandhan). Yearly festivals are observed in regular (Nija) months, not Adhika
months. Because local sunrise and sunset matter, a festival can correctly fall on different
dates in different cities; `occurrence_id` stays the same everywhere.

### Example (abridged)

```json
{
  "date": "2026-10-10",
  "city": { "id": "6167865", "name": "Toronto", "region": "Ontario", "timezone": "America/Toronto" },
  "profile": { "id": "north-indian-smarta", "rule_version": "2026.10.1", "ayanamsha": "lahiri" },
  "sun": { "sunrise": { "status": "occurs", "time": "2026-10-10T07:25:57-04:00" } },
  "tithi": {
    "at_sunrise": { "number": 30, "id": "krishna-amavasya", "name": "Amavasya",
                    "start": "2026-10-09T12:06:19-04:00", "end": "2026-10-10T11:50:07-04:00" },
    "spans": [ "...every Tithi overlapping sunrise -> next sunrise..." ]
  },
  "timings": [
    { "id": "rahu_kalam", "kind": "inauspicious", "applicable": true,
      "start": "2026-10-10T10:15:04-04:00", "end": "2026-10-10T11:39:38-04:00" }
  ]
}
```

## Conventions

| Topic | Convention |
|---|---|
| Ayanamsha | Lahiri (Chitrapaksha) |
| Day anchor | Local sunrise. `at_sunrise` is the value in force at sunrise; `spans` lists every span between sunrise and the next sunrise, with full local dates |
| Sunrise/sunset | Upper limb of the Sun with standard atmospheric refraction |
| Times | ISO 8601 with UTC offset, in the location's timezone, to the second. Reference panchangs display times rounded to the nearest minute |
| Timezones | IANA IDs, resolved with the bundled `tzdata` package (never the host OS copy) |
| Rise/set events | Sunrise/sunset: within the local civil date. Moonrise/moonset: within the Panchang day (sunrise to next sunrise), as Drik Panchang does, so a moonrise at 2 AM appears on the previous date's Panchang with its full date. If none occurs, `status` is `no_event` and `next_time` gives the next occurrence |
| Rahu Kalam, Yamaganda, Gulika Kalam | One-eighth of daytime; part numbers per weekday in the profile |
| Abhijit Muhurta | 8th of 15 daytime muhurtas; avoided on Wednesdays (`applicable: false`) |
| Brahma Muhurta | 14th of 15 night muhurtas (night = 24 h − daytime) |
| Supported dates | 2020-01-01 to 2035-12-31 by default (`VP_MIN_DATE`, `VP_MAX_DATE`) |

## Architecture

```
api/v1      HTTP only: parse requests, shape responses, map errors
  ↓
services    Use cases: resolve location, check date range, cache results
  ↓
domain      Panchang calculations (domain/panchang/), Location
  ↓
rules       Versioned tradition profiles (TOML data)
  ↓
astronomy   Swiss Ephemeris adapter: the ONLY module that imports swisseph

infra       City catalogue repository (CSV today, a database later)
```

Each layer imports only the layers below it; `tests/test_architecture.py` enforces this.
New capabilities (festivals, Muhurta search, ...) are added as new `domain/` modules.

## Development

```bash
uv run pytest            # full test suite
uv run ruff check .      # lint
uv run ruff format .     # format
```

Tests include Drik Panchang reference comparisons (`test_reference_drik.py`) and edge cases
(`test_regression_edge_cases.py`): DST transitions, Tithis ending after midnight,
no-moonrise days, polar night, half-hour timezones and leap days.

To refresh the city catalogue from GeoNames:

```bash
uv run python scripts/build_city_catalogue.py --countries CA,US,IN --min-population 5000
```

### Configuration

| Variable | Default |
|---|---|
| `VP_MIN_DATE`, `VP_MAX_DATE` | `2020-01-01`, `2035-12-31` |
| `VP_CACHE_SIZE` | `4096` results |
| `VP_CITIES_PATH` | bundled catalogue |
| `VP_CORS_ORIGINS` | `*` (comma-separated list) |

## Licence and data

- Code: [GNU AGPL v3.0 or later](LICENSE). If you run a modified version as a network
  service, you must offer its source code to its users.
- Swiss Ephemeris (via [pyswisseph](https://github.com/astrorigin/pyswisseph)): AGPL,
  © Astrodienst AG.
- City data: © [GeoNames](https://www.geonames.org), licensed
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See [NOTICE](NOTICE).
- Timezone data: [IANA tz database](https://www.iana.org/time-zones), public domain.
