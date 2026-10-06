import pytest

VALID = {
    "id": "t1",
    "start": "2026-10-01T08:10:00+05:00",
    "end": "2026-10-01T08:32:00+05:00",
    "amount": 2400,
    "payment": "card",
    "commission": 360,
}
MISSING = object()  # patch value that removes the field from the body


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
        pytest.param({"amount": 2400.0}, None, id="amount float"),
        pytest.param({"amount": "2400"}, None, id="amount string"),
        pytest.param({"amount": True}, None, id="amount bool"),
        pytest.param({"commission": "360"}, None, id="commission string"),
        pytest.param({"amount": 2**63, "commission": 0}, None, id="amount above int64"),
        pytest.param({"payment": "Cash"}, None, id="payment wrong case"),
        pytest.param({"payment": "crypto"}, None, id="payment unknown"),
        pytest.param({"start": "2026-10-01T08:10:00"}, "timezone offset required", id="start without offset"),
        pytest.param({"end": "2026-10-01T08:32:00"}, "timezone offset required", id="end without offset"),
        pytest.param({"start": 1759288200, "end": 1759289520}, None, id="unix timestamps"),
        pytest.param({"start": "yesterday"}, None, id="start not a date"),
        pytest.param({"note": "airport"}, "unknown field: note", id="extra field"),
        pytest.param({"comission": 360}, "unknown field: comission", id="misspelled field"),
        pytest.param({"amount": None}, None, id="amount null"),
        pytest.param({"id": None}, None, id="id null"),
        pytest.param({"payment": MISSING}, None, id="payment missing"),
        pytest.param({"start": MISSING}, None, id="start missing"),
    ],
)
def test_invalid_trip_is_rejected(client, patch, message):
    body = {key: value for key, value in {**VALID, **patch}.items() if value is not MISSING}

    response = client.post("/api/trips", json=body)

    assert response.status_code == 422, response.text
    if message is not None:
        assert any(message in error["msg"] for error in response.json()["detail"]), response.text
