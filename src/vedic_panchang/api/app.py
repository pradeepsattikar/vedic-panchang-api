from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from vedic_panchang import __version__
from vedic_panchang.api.errors import register_error_handlers
from vedic_panchang.api.hosting import RateLimit, ResponseHeaders
from vedic_panchang.api.v1.routes import router as v1_router
from vedic_panchang.config import Settings
from vedic_panchang.infra.city_repository import CityRepository
from vedic_panchang.rules.profiles import load_profiles
from vedic_panchang.services.panchang_service import PanchangService

DESCRIPTION = """
Deterministic Vedic Panchang calculations on the Swiss Ephemeris: Tithi, Nakshatra, Yoga,
Karana, sunrise/sunset, moonrise/moonset, Rahu Kalam, Yamaganda, Gulika Kalam, Abhijit and
Brahma Muhurta, for any catalogue city or any coordinates.

Every value comes from an astronomical calculation; nothing is generated or estimated.
Responses carry the engine version, rule version and calculation profile used.

Source code (AGPL-3.0): https://github.com/pradeepsattikar/vedic-panchang-api
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="Vedic Panchang API",
        version=__version__,
        description=DESCRIPTION,
        license_info={"name": "AGPL-3.0-or-later", "identifier": "AGPL-3.0-or-later"},
    )
    app.state.panchang_service = PanchangService(
        settings=settings,
        cities=CityRepository.from_csv(settings.cities_path),
        profiles=load_profiles(),
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["GET"]
    )
    app.add_middleware(ResponseHeaders)
    # Outermost: refuse floods before any work is done.
    app.add_middleware(
        RateLimit,
        per_minute=settings.rate_limit_per_minute,
        trust_proxy=settings.trust_proxy,
    )
    register_error_handlers(app)
    app.include_router(v1_router)

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/docs")

    return app
