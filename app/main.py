"""FastAPI application: routes and startup."""

from fastapi import FastAPI

from app.config import Settings
from app.models import Trip


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Driver shift diary")

    @app.post("/api/trips", status_code=201)
    def add_trip(trip: Trip) -> Trip:
        return trip

    return app


app = create_app()
