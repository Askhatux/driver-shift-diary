import dataclasses
import json
import logging
from pathlib import Path

import pytest

from fastapi.testclient import TestClient

from app.main import create_app

T1 = {
    "id": "t1",
    "start": "2026-10-01T08:10:00+05:00",
    "end": "2026-10-01T08:32:00+05:00",
    "amount": 2400,
    "payment": "card",
    "commission": 360,
}
T2 = {
    "id": "t2",
    "start": "2026-10-01T09:05:00+05:00",
    "end": "2026-10-01T09:20:00+05:00",
    "amount": 1500,
    "payment": "cash",
    "commission": 225,
}


def day_trip_ids(settings, day="2026-10-01"):
    """Start the app (which loads the trips file) and list trip ids of the day."""
    with TestClient(create_app(settings)) as client:
        return [trip["id"] for trip in client.get(f"/api/days/{day}").json()["trips"]]


def test_trips_file_is_loaded_at_startup(settings):
    settings.trips_file.write_text(json.dumps([T1, T2]))

    assert day_trip_ids(settings) == ["t1", "t2"]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (None, "not found"),
        ('[{"id": "t1",', "cannot read"),
        ('{"id": "t1"}', "must contain a JSON array"),
    ],
    ids=["missing", "broken json", "not an array"],
)
def test_unusable_file_is_logged_and_server_starts_empty(settings, caplog, content, message):
    caplog.set_level(logging.INFO, logger="app.seed")
    if content is not None:
        settings.trips_file.write_text(content)

    assert day_trip_ids(settings) == []
    assert message in caplog.text


def test_loading_file_twice_does_not_duplicate(settings, caplog):
    caplog.set_level(logging.INFO, logger="app.seed")
    settings.trips_file.write_text(json.dumps([T1, T2]))

    day_trip_ids(settings)  # first start
    caplog.clear()

    assert day_trip_ids(settings) == ["t1", "t2"]  # second start, same database
    assert "added 0, unchanged 2, rejected 0" in caplog.text


def test_repository_data_file_loads_without_rejections(settings, caplog):
    caplog.set_level(logging.INFO, logger="app.seed")
    settings = dataclasses.replace(settings, trips_file=Path(__file__).parent.parent / "data" / "trips.json")

    assert day_trip_ids(settings, "2026-10-01") == ["t1", "t2", "t3", "t4"]
    assert "added 7, unchanged 0, rejected 0" in caplog.text


def test_bad_records_are_skipped_and_reported(settings, caplog):
    caplog.set_level(logging.INFO, logger="app.seed")
    settings.trips_file.write_text(
        json.dumps([T1, {**T2, "amount": 0}, {**T1, "amount": 9999}, "not a trip"])
    )

    assert day_trip_ids(settings) == ["t1"]
    assert "added 1, unchanged 0, rejected 3" in caplog.text
    assert "t2: amount: Input should be greater than 0" in caplog.text
    assert "trip t1 already exists with different data" in caplog.text
    assert "#4:" in caplog.text
