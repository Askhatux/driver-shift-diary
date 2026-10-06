"""FastAPI application: routes and startup."""

import sqlite3
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response

from app import db
from app.config import Settings, load_settings
from app.models import Day, Trip
from app.summary import summarize


def _in_tz(trip: Trip, tz: timezone) -> Trip:
    return trip.model_copy(update={"start": trip.start.astimezone(tz), "end": trip.end.astimezone(tz)})


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Settings are read at startup, not at import, so a bad value stops the server here.
        app.state.settings = settings or load_settings()
        db.init_db(app.state.settings.db_path)
        yield

    app = FastAPI(title="Driver shift diary", lifespan=lifespan)

    def get_settings(request: Request) -> Settings:
        return request.app.state.settings

    def get_conn(settings: Annotated[Settings, Depends(get_settings)]) -> Iterator[sqlite3.Connection]:
        conn = db.connect(settings.db_path)
        try:
            yield conn
        finally:
            conn.close()

    SettingsDep = Annotated[Settings, Depends(get_settings)]
    ConnDep = Annotated[sqlite3.Connection, Depends(get_conn)]

    @app.post("/api/trips", status_code=201)
    def add_trip(trip: Trip, response: Response, settings: SettingsDep, conn: ConnDep) -> Trip:
        saved, created = db.save_trip(conn, trip)
        if not created:
            response.status_code = 200
        return _in_tz(saved, settings.day_tz)

    @app.get("/api/days/{day}")
    def get_day(day: date, settings: SettingsDep, conn: ConnDep) -> Day:
        day_start = datetime.combine(day, time.min, tzinfo=settings.day_tz)
        trips = db.trips_between(conn, day_start, day_start + timedelta(days=1))
        return Day(
            date=day,
            summary=summarize(trips),
            trips=[_in_tz(trip, settings.day_tz) for trip in trips],
        )

    return app


app = create_app()
