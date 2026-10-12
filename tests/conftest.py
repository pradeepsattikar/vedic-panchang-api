from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from vedic_panchang.api.app import create_app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(scope="session")
def daily(client):
    """Fetch a daily Panchang (city_id=... or lat/lon/tz=...) and return the JSON body."""

    def fetch(day: str, **params) -> dict:
        response = client.get("/v1/panchang/daily", params={"date": day, **params})
        assert response.status_code == 200, response.text
        return response.json()

    return fetch


def minutes_apart(iso_time: str, expected: str) -> int:
    """Whole minutes between an API timestamp (rounded to the minute) and 'YYYY-MM-DDTHH:MM'.

    Reference panchangs such as Drik Panchang display times rounded to the minute.
    """
    actual = datetime.fromisoformat(iso_time)
    rounded_minutes = round((actual.hour * 3600 + actual.minute * 60 + actual.second) / 60)
    wanted = datetime.fromisoformat(expected)
    day_diff = (actual.date() - wanted.date()).days
    return abs(day_diff * 1440 + rounded_minutes - (wanted.hour * 60 + wanted.minute))
