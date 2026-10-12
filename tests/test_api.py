"""HTTP contract: request validation, structured errors, catalogue and metadata."""

import pytest


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_response_carries_versions_and_request_context(daily):
    body = daily("2026-10-10", city_id="1259229")
    assert body["request"] == {
        "date": "2026-10-10",
        "city_id": "1259229",
        "latitude": None,
        "longitude": None,
        "timezone": None,
        "profile": "north-indian-smarta",
    }
    assert body["city"]["name"] == "Pune"
    assert body["location"]["timezone"] == "Asia/Kolkata"
    assert body["profile"]["rule_version"]
    assert body["engine"]["library_version"]
    assert body["api_version"]
    assert body["generated_at"]


def test_coordinates_work_anywhere(daily):
    body = daily("2026-10-10", lat=-33.8688, lon=151.2093, tz="Australia/Sydney")
    assert body["city"] is None
    assert body["sun"]["sunrise"]["time"].endswith("+11:00")


def test_date_defaults_to_today_at_the_location(client):
    response = client.get("/v1/panchang/daily", params={"city_id": "6167865"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("params", "status", "code"),
    [
        ({"city_id": "0"}, 404, "city_not_found"),
        ({"city_id": "6167865", "date": "2019-12-31"}, 422, "date_out_of_range"),
        ({"city_id": "6167865", "date": "2036-01-01"}, 422, "date_out_of_range"),
        ({"city_id": "6167865", "date": "2026-02-30"}, 422, "invalid_request"),
        ({"city_id": "6167865", "profile": "nope"}, 422, "unknown_profile"),
        ({"lat": 43.7, "lon": -79.4}, 422, "invalid_request"),
        ({"city_id": "6167865", "lat": 43.7, "lon": -79.4, "tz": "America/Toronto"}, 422,
         "invalid_request"),
        ({"lat": 43.7, "lon": -79.4, "tz": "Not/AZone"}, 422, "invalid_location"),
        ({"lat": 95, "lon": -79.4, "tz": "America/Toronto"}, 422, "invalid_request"),
    ],
)  # fmt: skip
def test_errors_are_structured_and_preserve_request(client, params, status, code):
    response = client.get("/v1/panchang/daily", params=params)
    assert response.status_code == status
    body = response.json()
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    assert body["request"]["path"] == "/v1/panchang/daily"
    for key, value in params.items():
        assert body["request"][key] == str(value)


def test_city_search_is_case_and_accent_insensitive(client):
    results = client.get("/v1/cities", params={"q": "MONTREAL"}).json()
    assert results[0]["name"] == "Montréal"
    assert results[0]["country_code"] == "CA"


def test_city_search_distinguishes_same_name_cities(client):
    results = client.get("/v1/cities", params={"q": "hyderabad"}).json()
    assert results[0]["country_code"] == "IN"
    assert len({r["id"] for r in results}) == len(results)


def test_city_search_country_filter(client):
    results = client.get("/v1/cities", params={"q": "london", "country": "us"}).json()
    assert results and all(r["country_code"] == "US" for r in results)


def test_get_city_and_nearest(client):
    assert client.get("/v1/cities/1275339").json()["name"] == "Mumbai"
    nearest = client.get("/v1/cities/nearest", params={"lat": 43.65, "lon": -79.38}).json()
    assert nearest["city"]["name"] == "Toronto"
    assert nearest["distance_km"] < 10
    assert client.get("/v1/cities/0").status_code == 404


def test_meta(client):
    meta = client.get("/v1/meta").json()
    assert meta["default_profile"] == "north-indian-smarta"
    assert meta["supported_dates"] == {"min_date": "2020-01-01", "max_date": "2035-12-31"}
    assert meta["city_catalogue"]["countries"] == ["CA", "IN", "US"]
    assert "GeoNames" in meta["city_catalogue"]["attribution"]
    assert meta["license"] == "AGPL-3.0-or-later"
    assert meta["timezone_data_version"]
