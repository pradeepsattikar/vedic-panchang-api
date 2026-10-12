"""City catalogue backed by a CSV file (GeoNames data, CC BY 4.0).

Kept behind a small interface so it can move to a database later without changes above
the infrastructure layer.
"""

import csv
import math
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from vedic_panchang.domain.location import Location


@dataclass(frozen=True)
class City:
    id: str  # GeoNames ID: stable, and distinguishes same-name cities
    name: str
    ascii_name: str
    region: str
    region_code: str
    country_code: str
    country: str
    latitude: float
    longitude: float
    elevation_m: float
    timezone: str
    population: int

    @property
    def location(self) -> Location:
        return Location(self.latitude, self.longitude, self.timezone, self.elevation_m)


def _normalise(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold().strip()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


class CityRepository:
    def __init__(self, cities: list[City]):
        self._by_id = {c.id: c for c in cities}
        # Ordered by population so the best-known match comes first.
        self._ranked = sorted(cities, key=lambda c: -c.population)
        self._keys = [({_normalise(c.name), _normalise(c.ascii_name)}, c) for c in self._ranked]

    @classmethod
    def from_csv(cls, path: Path) -> "CityRepository":
        with path.open(encoding="utf-8", newline="") as f:
            cities = [
                City(
                    id=row["id"],
                    name=row["name"],
                    ascii_name=row["ascii_name"],
                    region=row["region"],
                    region_code=row["region_code"],
                    country_code=row["country_code"],
                    country=row["country"],
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    elevation_m=float(row["elevation_m"] or 0),
                    timezone=row["timezone"],
                    population=int(row["population"]),
                )
                for row in csv.DictReader(f)
            ]
        return cls(cities)

    def __len__(self) -> int:
        return len(self._by_id)

    def countries(self) -> list[str]:
        return sorted({c.country_code for c in self._ranked})

    def get(self, city_id: str) -> City | None:
        return self._by_id.get(city_id)

    def search(self, query: str, country_code: str | None = None, limit: int = 10) -> list[City]:
        """Case- and accent-insensitive name search: exact matches first, then prefixes."""
        q = _normalise(query)
        if not q:
            return []
        country = country_code.upper() if country_code else None
        exact, prefix = [], []
        for keys, city in self._keys:
            if country and city.country_code != country:
                continue
            if q in keys:
                exact.append(city)
            elif any(k.startswith(q) for k in keys):
                prefix.append(city)
            if len(exact) >= limit:
                break
        return (exact + prefix)[:limit]

    def nearest(self, latitude: float, longitude: float) -> tuple[City, float]:
        """Closest catalogue city and its distance in km."""
        city = min(
            self._ranked,
            key=lambda c: _haversine_km(latitude, longitude, c.latitude, c.longitude),
        )
        return city, _haversine_km(latitude, longitude, city.latitude, city.longitude)
