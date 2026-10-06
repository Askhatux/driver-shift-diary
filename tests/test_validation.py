import pytest

VALID = {
    "id": "t1",
    "start": "2026-10-01T08:10:00+05:00",
    "end": "2026-10-01T08:32:00+05:00",
    "amount": 2400,
    "payment": "card",
    "commission": 360,
}


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        pytest.param({"amount": 0}, None, id="amount zero"),
        pytest.param({"amount": -100}, None, id="amount negative"),
    ],
)
def test_invalid_trip_is_rejected(client, patch, message):
    response = client.post("/api/trips", json={**VALID, **patch})

    assert response.status_code == 422, response.text
    if message is not None:
        assert any(message in error["msg"] for error in response.json()["detail"]), response.text
