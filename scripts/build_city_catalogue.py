"""Build the bundled city catalogue from GeoNames.

Usage:
    uv run python scripts/build_city_catalogue.py --countries CA,US,IN --min-population 5000

Data: GeoNames (https://www.geonames.org), licensed CC BY 4.0. Downloads cities5000 (all
populated places with population >= 5000), country names and first-level region names,
and writes src/vedic_panchang/infra/data/cities.csv.
"""

import argparse
import csv
import io
import urllib.request
import zipfile
from pathlib import Path

BASE_URL = "https://download.geonames.org/export/dump/"
OUTPUT = Path(__file__).resolve().parents[1] / "src/vedic_panchang/infra/data/cities.csv"

# Historical, abandoned or destroyed places are not useful for a Panchang, and
# neighbourhoods (PPLX) would make "nearest city" return e.g. "Moss Park" for Toronto.
EXCLUDED_FEATURE_CODES = {"PPLH", "PPLQ", "PPLW", "PPLCH", "PPLX"}

FIELDS = [
    "id", "name", "ascii_name", "region", "region_code", "country_code", "country",
    "latitude", "longitude", "elevation_m", "timezone", "population",
]  # fmt: skip


def fetch(name: str) -> bytes:
    with urllib.request.urlopen(BASE_URL + name, timeout=120) as response:
        return response.read()


def tsv_rows(text: str):
    for line in text.splitlines():
        if line and not line.startswith("#"):
            yield line.split("\t")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--countries", default="CA,US,IN", help="ISO country codes")
    parser.add_argument("--min-population", type=int, default=5000)
    args = parser.parse_args()
    countries = {c.strip().upper() for c in args.countries.split(",")}

    country_names = {row[0]: row[4] for row in tsv_rows(fetch("countryInfo.txt").decode())}
    region_names = {row[0]: row[1] for row in tsv_rows(fetch("admin1CodesASCII.txt").decode())}
    with zipfile.ZipFile(io.BytesIO(fetch("cities5000.zip"))) as archive:
        cities_text = archive.read("cities5000.txt").decode()

    rows = []
    for c in tsv_rows(cities_text):
        country_code, feature_code = c[8], c[7]
        population = int(c[14] or 0)
        if country_code not in countries or feature_code in EXCLUDED_FEATURE_CODES:
            continue
        if population < args.min_population:
            continue
        elevation = c[15] or (c[16] if c[16] not in ("", "-9999") else "0")
        rows.append({
            "id": c[0],
            "name": c[1],
            "ascii_name": c[2],
            "region": region_names.get(f"{country_code}.{c[10]}", ""),
            "region_code": c[10],
            "country_code": country_code,
            "country": country_names.get(country_code, country_code),
            "latitude": c[4],
            "longitude": c[5],
            "elevation_m": elevation,
            "timezone": c[17],
            "population": population,
        })  # fmt: skip

    rows.sort(key=lambda r: (r["country_code"], -r["population"], r["name"]))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} cities for {sorted(countries)} to {OUTPUT}")


if __name__ == "__main__":
    main()
