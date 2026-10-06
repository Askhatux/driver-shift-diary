from datetime import timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(
        day_tz=timezone(timedelta(hours=5)),
        trips_file=tmp_path / "trips.json",
        db_path=tmp_path / "trips.db",
    )


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client
