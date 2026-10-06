"""FastAPI application: routes and startup."""

import logging
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager, closing
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import db, seed
from app.config import Settings, load_settings
from app.models import Day, DayParam, Trip
from app.summary import summarize

STATIC_DIR = Path(__file__).parent.parent / "static"


def _in_tz(trip: Trip, tz: timezone) -> Trip:
    return trip.model_copy(update={"start": trip.start.astimezone(tz), "end": trip.end.astimezone(tz)})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_app(settings: Settings | None = None, now: Callable[[], datetime] = _utc_now) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Settings are read at startup, not at import, so a bad value stops the server here.
        app.state.settings = settings or load_settings()
        db.init_db(app.state.settings.db_path)
        with closing(db.connect(app.state.settings.db_path)) as conn:
            seed.load_trips_file(conn, app.state.settings.trips_file)
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
        try:
            saved, created = db.save_trip(conn, trip)
        except db.TripConflict as error:
            raise HTTPException(status_code=409, detail=str(error))
        if not created:
            response.status_code = 200
        return _in_tz(saved, settings.day_tz)

    @app.get("/api/days/{day}")
    def get_day(day: DayParam, settings: SettingsDep, conn: ConnDep) -> Day:
        if day == "today":
            day = now().astimezone(settings.day_tz).date()
        day_start = datetime.combine(day, time.min, tzinfo=settings.day_tz)
        trips = db.trips_between(conn, day_start, day_start + timedelta(days=1))
        return Day(
            date=day,
            summary=summarize(trips),
            trips=[_in_tz(trip, settings.day_tz) for trip in trips],
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def client_page(settings: SettingsDep) -> HTMLResponse:
        # The client needs the day offset to build trip times; "+05:00" is the tail of an ISO time.
        offset = datetime.now(settings.day_tz).isoformat()[-6:]
        page = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(page.replace("{{DAY_TZ_OFFSET}}", offset))

    return app


# Uvicorn configures only its own loggers; this makes app.* messages (the seed report) visible.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
app = create_app()
