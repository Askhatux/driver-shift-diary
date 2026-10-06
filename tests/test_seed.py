import json

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
