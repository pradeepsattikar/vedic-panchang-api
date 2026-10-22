"""Hosting protections: rate limiting and response headers."""

from fastapi.testclient import TestClient

from vedic_panchang.api.app import create_app
from vedic_panchang.config import Settings


def _client(**settings) -> TestClient:
    return TestClient(create_app(Settings(**settings)))


def test_rate_limit_answers_429_with_retry_after():
    client = _client(rate_limit_per_minute=3)
    for _ in range(3):
        assert client.get("/v1/meta").status_code == 200
    response = client.get("/v1/meta")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert int(response.headers["retry-after"]) >= 1
    assert client.get("/health").status_code == 200  # health checks are never limited


def test_rate_limit_counts_each_forwarded_client_separately():
    client = _client(rate_limit_per_minute=1, trust_proxy=True)
    assert (
        client.get("/v1/meta", headers={"x-forwarded-for": "1.1.1.1, 10.0.0.1"}).status_code == 200
    )
    assert client.get("/v1/meta", headers={"x-forwarded-for": "2.2.2.2"}).status_code == 200
    assert client.get("/v1/meta", headers={"x-forwarded-for": "1.1.1.1"}).status_code == 429


def test_no_limit_by_default_and_cacheable_answers():
    client = _client()
    for _ in range(20):
        response = client.get("/v1/meta")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=60"
    assert response.headers["x-content-type-options"] == "nosniff"
    error = client.get("/v1/cities/0")
    assert "cache-control" not in error.headers


def test_only_allowed_origins_get_cors():
    client = _client(cors_origins=("https://app.example",))
    allowed = client.get("/v1/meta", headers={"origin": "https://app.example"})
    assert allowed.headers["access-control-allow-origin"] == "https://app.example"
    other = client.get("/v1/meta", headers={"origin": "https://elsewhere.example"})
    assert "access-control-allow-origin" not in other.headers


def test_data_fingerprint_on_every_v1_answer_and_in_meta():
    client = _client()
    meta = client.get("/v1/meta")
    fingerprint = meta.json()["data_fingerprint"]
    assert len(fingerprint) == 16
    assert meta.headers["x-data-fingerprint"] == fingerprint
    assert client.get("/v1/cities/0").headers["x-data-fingerprint"] == fingerprint  # errors too
    assert "x-data-fingerprint" not in client.get("/health").headers


def test_data_fingerprint_changes_when_any_file_changes(tmp_path, monkeypatch):
    from vedic_panchang.api import fingerprint

    (tmp_path / "rules.toml").write_text("tithi = 1")
    monkeypatch.setattr(fingerprint, "_PACKAGE", tmp_path)
    fingerprint.data_fingerprint.cache_clear()
    before = fingerprint.data_fingerprint()
    (tmp_path / "rules.toml").write_text("tithi = 2")
    fingerprint.data_fingerprint.cache_clear()
    after = fingerprint.data_fingerprint()
    fingerprint.data_fingerprint.cache_clear()
    assert before != after
