from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from vedic_panchang.api.errors import BadRequestError
from vedic_panchang.api.v1 import schemas
from vedic_panchang.services.panchang_service import PanchangResult, PanchangService

router = APIRouter(prefix="/v1")

SOURCE_CODE_URL = "https://github.com/pradeepsattikar/vedic-panchang-api"
GEONAMES_ATTRIBUTION = "City data © GeoNames (geonames.org), licensed CC BY 4.0"


def get_service(request: Request) -> PanchangService:
    return request.app.state.panchang_service


Service = Annotated[PanchangService, Depends(get_service)]


def _to_response(result: PanchangResult, request_ctx: dict) -> schemas.DailyPanchangOut:
    p = result.panchang
    validate = schemas.CelestialEventOut.model_validate
    return schemas.DailyPanchangOut(
        request=schemas.RequestContextOut(**request_ctx, date=p.date, profile=result.profile.id),
        date=p.date,
        location=schemas.LocationOut.model_validate(result.location),
        city=schemas.CityOut.model_validate(result.city) if result.city else None,
        profile=schemas.ProfileOut.model_validate(result.profile),
        engine=schemas.EngineOut.model_validate(result.engine),
        api_version=result.api_version,
        timezone_data_version=result.timezone_data_version,
        generated_at=result.generated_at,
        vara=schemas.VaraOut.model_validate(p.vara),
        masa=schemas.LunarMonthsOut.model_validate(p.masa),
        day_window=schemas.DayWindowOut.model_validate(p.day_window),
        sun=schemas.SunOut(sunrise=validate(p.sunrise), sunset=validate(p.sunset)),
        moon=schemas.MoonOut(moonrise=validate(p.moonrise), moonset=validate(p.moonset)),
        tithi=schemas.ElementOut.model_validate(p.tithi),
        nakshatra=schemas.ElementOut.model_validate(p.nakshatra),
        yoga=schemas.ElementOut.model_validate(p.yoga),
        karana=schemas.ElementOut.model_validate(p.karana),
        timings=[schemas.TimingOut.model_validate(t) for t in p.timings],
    )


@router.get("/panchang/daily", response_model=schemas.DailyPanchangOut, tags=["panchang"])
def daily_panchang(
    service: Service,
    date_: Annotated[
        date | None,
        Query(alias="date", description="Local civil date (YYYY-MM-DD). Default: today there"),
    ] = None,
    city_id: Annotated[str | None, Query(description="City ID from /v1/cities")] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    tz: Annotated[str | None, Query(description="IANA timezone, e.g. Asia/Kolkata")] = None,
    alt: Annotated[float, Query(description="Altitude in metres")] = 0.0,
    profile: Annotated[str | None, Query(description="Calculation profile ID")] = None,
):
    """Daily Panchang for a catalogue city (`city_id`) or any coordinates (`lat`, `lon`, `tz`).

    Element values are anchored at local sunrise; every span overlapping the Panchang day
    (sunrise to next sunrise) is listed with start and end times.
    """
    coordinates = (lat, lon, tz)
    if city_id is not None:
        if any(v is not None for v in coordinates):
            raise BadRequestError("Give either city_id or lat/lon/tz, not both")
        result = service.daily_for_city(city_id, date_, profile)
        ctx = {"city_id": city_id}
    elif all(v is not None for v in coordinates):
        result = service.daily_for_coordinates(lat, lon, tz, alt, date_, profile)
        ctx = {"latitude": lat, "longitude": lon, "timezone": tz}
    else:
        raise BadRequestError("Give either city_id, or all of lat, lon and tz")
    return _to_response(result, ctx)


@router.get("/cities", response_model=list[schemas.CityOut], tags=["cities"])
def search_cities(
    service: Service,
    q: Annotated[str, Query(min_length=1, max_length=100, description="City name or prefix")],
    country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """Search the city catalogue by name (case- and accent-insensitive)."""
    return service.cities.search(q, country, limit)


@router.get("/cities/nearest", response_model=schemas.NearestCityOut, tags=["cities"])
def nearest_city(
    service: Service,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
):
    """Closest catalogue city to a point (e.g. from optional device location)."""
    city, distance = service.cities.nearest(lat, lon)
    return schemas.NearestCityOut(
        city=schemas.CityOut.model_validate(city), distance_km=round(distance, 1)
    )


@router.get("/cities/{city_id}", response_model=schemas.CityOut, tags=["cities"])
def get_city(service: Service, city_id: str):
    return service.city(city_id)


@router.get("/meta", response_model=schemas.MetaOut, tags=["meta"])
def meta(service: Service):
    """API, engine and rule versions, supported dates and available profiles."""
    profiles = service.profiles
    return schemas.MetaOut(
        api_version=service.api_version,
        engine=schemas.EngineOut.model_validate(service.engine),
        timezone_data_version=service.timezone_data_version,
        default_profile=profiles.default_id,
        profiles=[schemas.ProfileOut.model_validate(p) for p in profiles.profiles.values()],
        supported_dates=schemas.DateRangeOut(
            min_date=service.settings.min_date, max_date=service.settings.max_date
        ),
        city_catalogue=schemas.CatalogueOut(
            city_count=len(service.cities),
            countries=service.cities.countries(),
            attribution=GEONAMES_ATTRIBUTION,
        ),
        source_code=SOURCE_CODE_URL,
        license="AGPL-3.0-or-later",
    )
