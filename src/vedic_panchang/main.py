"""ASGI entry point: ``uvicorn vedic_panchang.main:app``."""

from vedic_panchang.api.app import create_app

app = create_app()
