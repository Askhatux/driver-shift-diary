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
