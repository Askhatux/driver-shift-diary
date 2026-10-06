T1 = {
    "id": "t1",
    "start": "2026-10-01T08:10:00+05:00",
    "end": "2026-10-01T08:32:00+05:00",
    "amount": 2400,
    "payment": "card",
    "commission": 360,
}


def test_new_trip_is_created(client):
    response = client.post("/api/trips", json=T1)

    assert response.status_code == 201
    assert response.json() == T1


def test_repeated_trip_is_not_duplicated(client):
    first = client.post("/api/trips", json=T1)
    second = client.post("/api/trips", json=T1)

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json() == T1
    day = client.get("/api/days/2026-10-01").json()
    assert [trip["id"] for trip in day["trips"]] == ["t1"]
