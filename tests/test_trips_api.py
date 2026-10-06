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


def test_same_moment_in_other_offset_is_a_repeat(client):
    client.post("/api/trips", json=T1)

    response = client.post(
        "/api/trips",
        json={**T1, "start": "2026-10-01T06:10:00+03:00", "end": "2026-10-01T06:32:00+03:00"},
    )

    assert response.status_code == 200
    assert response.json() == T1


def test_same_id_with_different_data_is_rejected(client):
    client.post("/api/trips", json=T1)

    response = client.post("/api/trips", json={**T1, "amount": 9999})

    assert response.status_code == 409
    assert response.json() == {"detail": "trip t1 already exists with different data"}
    day = client.get("/api/days/2026-10-01").json()
    assert [trip["amount"] for trip in day["trips"]] == [2400]
