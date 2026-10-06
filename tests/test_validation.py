import pytest

VALID = {
    "id": "t1",
    "start": "2026-10-01T08:10:00+05:00",
    "end": "2026-10-01T08:32:00+05:00",
    "amount": 2400,
    "payment": "card",
    "commission": 360,
}


@pytest.mark.parametrize("commission", [0, 2400], ids=["zero", "equal to amount"])
def test_commission_bounds_are_inclusive(client, commission):
    response = client.post("/api/trips", json={**VALID, "commission": commission})

    assert response.status_code == 201, response.text


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        pytest.param({"amount": 0}, None, id="amount zero"),
        pytest.param({"amount": -100}, None, id="amount negative"),
        pytest.param({"end": VALID["start"]}, "end must be later than start", id="end equals start"),
        pytest.param({"end": "2026-10-01T08:00:00+05:00"}, "end must be later than start", id="end before start"),
        pytest.param({"commission": -1}, None, id="commission negative"),
        pytest.param({"commission": 2401}, "commission must not exceed amount", id="commission above amount"),
    ],
)
def test_invalid_trip_is_rejected(client, patch, message):
    response = client.post("/api/trips", json={**VALID, **patch})

    assert response.status_code == 422, response.text
    if message is not None:
        assert any(message in error["msg"] for error in response.json()["detail"]), response.text
