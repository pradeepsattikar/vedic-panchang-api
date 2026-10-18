from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request

from vedic_panchang.api.v1 import schemas
from vedic_panchang.services.panchang_service import PanchangService, Place, Provenance

router = APIRouter(prefix="/v1")

SOURCE_CODE_URL = "https://github.com/pradeepsattikar/vedic-panchang-api"
GEONAMES_ATTRIBUTION = "City data © GeoNames (geonames.org), licensed CC BY 4.0"


def get_service(request: Request) -> PanchangService:
    return request.app.state.panchang_service


Service = Annotated[PanchangService, Depends(get_service)]


def get_place(
    service: Service,
    city_id: Annotated[str | None, Query(description="City ID from /v1/cities")] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    tz: Annotated[str | None, Query(description="IANA timezone, e.g. Asia/Kolkata")] = None,
    alt: Annotated[float, Query(description="Altitude in metres")] = 0.0,
) -> Place:
    """A catalogue city (`city_id`) or any coordinates (`lat`, `lon`, `tz`)."""
    return service.place(city_id, lat, lon, tz, alt)


PlaceParam = Annotated[Place, Depends(get_place)]
ProfileParam = Annotated[str | None, Query(description="Calculation profile ID")]


def _context(place: Place, provenance: Provenance) -> dict:
    return {
        "location": schemas.LocationOut.model_validate(place.location),
        "city": schemas.CityOut.model_validate(place.city) if place.city else None,
        "profile": schemas.ProfileOut.model_validate(provenance.profile),
        "festival_rule_version": provenance.festival_set.rule_version,
        "engine": schemas.EngineOut.model_validate(provenance.engine),
        "api_version": provenance.api_version,
        "timezone_data_version": provenance.timezone_data_version,
        "generated_at": provenance.generated_at,
    }


@router.get("/panchang/daily", response_model=schemas.DailyPanchangOut, tags=["panchang"])
def daily_panchang(
    service: Service,
    place: PlaceParam,
    date_: Annotated[
        date | None,
        Query(alias="date", description="Local civil date (YYYY-MM-DD). Default: today there"),
    ] = None,
    profile: ProfileParam = None,
):
    """Daily Panchang for a catalogue city or any coordinates.

    Element values are anchored at local sunrise; every span overlapping the Panchang day
    (sunrise to next sunrise) is listed with start and end times. Festivals and
    observances falling on the date are listed under `observances`.
    """
    result = service.daily(place, date_, profile)
    p = result.panchang
    event = schemas.CelestialEventOut.model_validate
    return schemas.DailyPanchangOut(
        request=schemas.RequestContextOut(
            **place.request, date=p.date, profile=result.provenance.profile.id
        ),
        date=p.date,
        **_context(place, result.provenance),
        vara=schemas.VaraOut.model_validate(p.vara),
        masa=schemas.LunarMonthsOut.model_validate(p.masa),
        day_window=schemas.DayWindowOut.model_validate(p.day_window),
        sun=schemas.SunOut(sunrise=event(p.sunrise), sunset=event(p.sunset)),
        moon=schemas.MoonOut(moonrise=event(p.moonrise), moonset=event(p.moonset)),
        tithi=schemas.ElementOut.model_validate(p.tithi),
        nakshatra=schemas.ElementOut.model_validate(p.nakshatra),
        yoga=schemas.ElementOut.model_validate(p.yoga),
        karana=schemas.ElementOut.model_validate(p.karana),
        sun_sign=schemas.ElementOut.model_validate(p.sun_sign),
        moon_sign=schemas.ElementOut.model_validate(p.moon_sign),
        sun_nakshatra=schemas.ElementOut.model_validate(p.sun_nakshatra),
        year=schemas.YearInfoOut.model_validate(p.year),
        grahas=schemas.GrahaPositionsOut.model_validate(p.grahas),
        timings=[schemas.TimingOut.model_validate(t) for t in p.timings],
        observances=[schemas.FestivalOut.model_validate(o) for o in result.observances],
    )


@router.get("/panchang/month", response_model=schemas.MonthOut, tags=["panchang"])
def month_panchang(
    service: Service,
    place: PlaceParam,
    year: Annotated[int | None, Query(description="Default: current year there")] = None,
    month: Annotated[int | None, Query(ge=1, le=12, description="Default: current month")] = None,
    profile: ProfileParam = None,
):
    """One compact summary per day of a month (Tithi and Nakshatra at sunrise, sunrise,
    sunset, Masa, festivals), for calendar views."""
    result = service.month(place, year, month, profile)
    event = schemas.CelestialEventOut.model_validate
    span = schemas.SpanOut.model_validate
    return schemas.MonthOut(
        request=schemas.MonthRequestOut(
            **place.request,
            year=result.year,
            month=result.month,
            profile=result.provenance.profile.id,
        ),
        year=result.year,
        month=result.month,
        **_context(place, result.provenance),
        days=[
            schemas.MonthDayOut(
                date=d.panchang.date,
                vara=schemas.VaraOut.model_validate(d.panchang.vara),
                masa=schemas.LunarMonthsOut.model_validate(d.panchang.masa),
                sunrise=event(d.panchang.sunrise),
                sunset=event(d.panchang.sunset),
                tithi_at_sunrise=d.panchang.tithi.at_sunrise and span(d.panchang.tithi.at_sunrise),
                nakshatra_at_sunrise=d.panchang.nakshatra.at_sunrise
                and span(d.panchang.nakshatra.at_sunrise),
                observances=[schemas.FestivalOut.model_validate(o) for o in d.observances],
            )
            for d in result.days
        ],
    )


def _festivals_response(service, place, year, profile, festival_id=None, category=None):
    result = service.festivals(place, year, profile, festival_id, category)
    return schemas.FestivalsOut(
        request=schemas.FestivalsRequestOut(
            **place.request,
            year=result.year,
            profile=result.provenance.profile.id,
            festival_id=festival_id,
            category=category,
        ),
        year=result.year,
        **_context(place, result.provenance),
        festivals=[schemas.FestivalOut.model_validate(o) for o in result.festivals],
    )


YearParam = Annotated[int | None, Query(description="Gregorian year. Default: current year")]


@router.get("/festivals", response_model=schemas.FestivalsOut, tags=["festivals"])
def festivals(
    service: Service,
    place: PlaceParam,
    year: YearParam = None,
    category: Annotated[Literal["major", "observance"] | None, Query()] = None,
    profile: ProfileParam = None,
):
    """Festivals and observances in a year, with their local dates at this place.

    Dates can correctly differ between places: each festival falls on the local day on
    which its Tithi prevails during the required part of the day (`kala`).
    """
    return _festivals_response(service, place, year, profile, category=category)


@router.get("/festivals/{festival_id}", response_model=schemas.FestivalsOut, tags=["festivals"])
def festival(
    service: Service,
    place: PlaceParam,
    festival_id: str,
    year: YearParam = None,
    profile: ProfileParam = None,
):
    """Occurrences of one festival in a year (monthly observances occur several times)."""
    return _festivals_response(service, place, year, profile, festival_id=festival_id)


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


@router.get("/muhurta/purposes", response_model=list[schemas.MuhurtaPurposeOut], tags=["muhurta"])
def muhurta_purposes(service: Service):
    """The purposes general muhurtas can be found for."""
    return [schemas.MuhurtaPurposeOut.model_validate(p) for p in service.muhurta_purposes()]


@router.get("/muhurta", response_model=schemas.MuhurtaOut, tags=["muhurta"])
def muhurta(
    service: Service,
    place: PlaceParam,
    purpose: Annotated[str, Query(description="Purpose ID from /v1/muhurta/purposes")],
    from_date: Annotated[
        date | None, Query(alias="from", description="First date (default: today there)")
    ] = None,
    days: Annotated[int, Query(ge=1, le=400, description="How many days to search")] = 180,
    profile: ProfileParam = None,
):
    """General muhurta windows for a purpose (e.g. Vivah, Griha Pravesh) at a place.

    Panchang Shuddhi only: Nakshatra, Tithi, weekday, Yoga, Bhadra, Gandanta, month, Chaturmas
    and Guru/Shukra asta, per the purpose's rules. Not based on anyone's birth chart and without
    Lagna Shuddhi; a family priest should confirm the final time.
    """
    result = service.muhurta(place, purpose, from_date, days, profile)
    p = result.provenance
    return schemas.MuhurtaOut(
        request=schemas.MuhurtaRequestOut(
            **place.request,
            purpose=purpose,
            from_date=result.first,
            days=days,
            profile=p.profile.id,
        ),  # fmt: skip
        purpose=schemas.MuhurtaPurposeOut.model_validate(result.purpose),
        from_date=result.first,
        to_date=result.last,
        location=schemas.LocationOut.model_validate(place.location),
        city=schemas.CityOut.model_validate(place.city) if place.city else None,
        profile=schemas.ProfileOut.model_validate(p.profile),
        engine=schemas.EngineOut.model_validate(p.engine),
        api_version=p.api_version,
        timezone_data_version=p.timezone_data_version,
        muhurta_rule_version=result.rules.rule_version,
        basis="General Panchang Shuddhi; not based on a personal birth chart or Lagna",
        generated_at=p.generated_at,
        windows=[schemas.MuhurtaWindowOut.model_validate(w) for w in result.windows],
    )


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
