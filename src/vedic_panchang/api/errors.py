"""Map domain/service errors to structured JSON errors that preserve the request context.

A failure is always reported as an error: never as a success with blank values, 00:00
times or another city's data.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from vedic_panchang.services.panchang_service import (
    CityNotFoundError,
    DateOutOfRangeError,
    FestivalNotFoundError,
    InvalidLocationError,
    LocationRequestError,
    UnknownProfileError,
    UnknownPurposeError,
)

logger = logging.getLogger(__name__)


def _error(request: Request, status: int, code: str, message: str, details=None):
    body = {
        "error": {"code": code, "message": message, "details": details},
        "request": {"path": request.url.path, **dict(request.query_params)},
    }
    return JSONResponse(status_code=status, content=body)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DateOutOfRangeError)
    async def _date_range(request: Request, exc: DateOutOfRangeError):
        details = {"min_date": exc.min_date.isoformat(), "max_date": exc.max_date.isoformat()}
        return _error(request, 422, "date_out_of_range", str(exc), details)

    @app.exception_handler(CityNotFoundError)
    async def _city(request: Request, exc: CityNotFoundError):
        return _error(request, 404, "city_not_found", str(exc))

    @app.exception_handler(UnknownPurposeError)
    async def _purpose(request: Request, exc: UnknownPurposeError):
        return _error(request, 404, "purpose_not_found", str(exc), {"available": exc.available})

    @app.exception_handler(UnknownProfileError)
    async def _profile(request: Request, exc: UnknownProfileError):
        return _error(request, 422, "unknown_profile", str(exc), {"available": exc.available})

    @app.exception_handler(InvalidLocationError)
    async def _location(request: Request, exc: InvalidLocationError):
        return _error(request, 422, "invalid_location", str(exc))

    @app.exception_handler(FestivalNotFoundError)
    async def _festival(request: Request, exc: FestivalNotFoundError):
        return _error(request, 404, "festival_not_found", str(exc))

    @app.exception_handler(LocationRequestError)
    async def _location_request(request: Request, exc: LocationRequestError):
        return _error(request, 422, "invalid_request", str(exc))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        problems = [
            {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return _error(request, 422, "invalid_request", "Invalid request parameters", problems)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        logger.exception("Calculation failed for %s", request.url)
        return _error(request, 500, "calculation_error", "The calculation could not be completed")
