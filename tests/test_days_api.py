def post_trip(client, id, start, end, amount=1000, payment="cash", commission=100):
    response = client.post(
        "/api/trips",
        json={"id": id, "start": start, "end": end, "amount": amount, "payment": payment, "commission": commission},
    )
    assert response.status_code == 201, response.text


def trip_ids(client, day):
    return [trip["id"] for trip in client.get(f"/api/days/{day}").json()["trips"]]


def test_day_of_task_example(client):
    post_trip(client, "t1", "2026-10-01T08:10:00+05:00", "2026-10-01T08:32:00+05:00", 2400, "card", 360)
    post_trip(client, "t2", "2026-10-01T09:05:00+05:00", "2026-10-01T09:20:00+05:00", 1500, "cash", 225)

    response = client.get("/api/days/2026-10-01")

    assert response.status_code == 200
    assert response.json() == {
        "date": "2026-10-01",
        "summary": {
            "trips_count": 2,
            "revenue": 3900,
            "commission": 585,
            "net": 3315,
            "by_payment": {
                "cash": {"trips_count": 1, "revenue": 1500, "commission": 225, "net": 1275},
                "card": {"trips_count": 1, "revenue": 2400, "commission": 360, "net": 2040},
            },
        },
        "trips": [
            {"id": "t1", "start": "2026-10-01T08:10:00+05:00", "end": "2026-10-01T08:32:00+05:00",
             "amount": 2400, "payment": "card", "commission": 360},
            {"id": "t2", "start": "2026-10-01T09:05:00+05:00", "end": "2026-10-01T09:20:00+05:00",
             "amount": 1500, "payment": "cash", "commission": 225},
        ],
    }


def test_empty_day_is_zeros_not_404(client):
    response = client.get("/api/days/2026-10-05")

    zeros = {"trips_count": 0, "revenue": 0, "commission": 0, "net": 0}
    assert response.status_code == 200
    assert response.json() == {
        "date": "2026-10-05",
        "summary": {**zeros, "by_payment": {"cash": zeros, "card": zeros}},
        "trips": [],
    }


def test_day_boundaries_follow_configured_offset_and_trip_start(client):
    post_trip(client, "late", "2026-10-01T23:59:00+05:00", "2026-10-02T00:10:00+05:00")
    post_trip(client, "across-midnight", "2026-10-01T23:50:00+05:00", "2026-10-02T00:15:00+05:00")
    post_trip(client, "midnight", "2026-10-02T00:00:00+05:00", "2026-10-02T00:20:00+05:00")

    assert trip_ids(client, "2026-10-01") == ["across-midnight", "late"]
    assert trip_ids(client, "2026-10-02") == ["midnight"]


def test_trip_sent_in_utc_lands_in_local_day_and_is_shown_in_local_time(client):
    post_trip(client, "z", "2026-10-01T20:30:00Z", "2026-10-01T20:50:00Z")

    trips = client.get("/api/days/2026-10-02").json()["trips"]

    assert [(t["id"], t["start"], t["end"]) for t in trips] == [
        ("z", "2026-10-02T01:30:00+05:00", "2026-10-02T01:50:00+05:00")
    ]
    assert trip_ids(client, "2026-10-01") == []


def test_trips_are_sorted_by_start_then_id(client):
    post_trip(client, "later", "2026-10-01T12:00:00+05:00", "2026-10-01T12:30:00+05:00")
    post_trip(client, "b", "2026-10-01T09:00:00+05:00", "2026-10-01T09:30:00+05:00")
    post_trip(client, "a", "2026-10-01T09:00:00+05:00", "2026-10-01T09:20:00+05:00")

    assert trip_ids(client, "2026-10-01") == ["a", "b", "later"]
