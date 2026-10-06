from datetime import datetime

from app.models import Trip
from app.summary import summarize


def make_trip(id: str, start: str, end: str, amount: int, payment: str, commission: int) -> Trip:
    return Trip(
        id=id,
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
        amount=amount,
        payment=payment,
        commission=commission,
    )


def test_summary_of_task_example():
    trips = [
        make_trip("t1", "2026-10-01T08:10:00+05:00", "2026-10-01T08:32:00+05:00", 2400, "card", 360),
        make_trip("t2", "2026-10-01T09:05:00+05:00", "2026-10-01T09:20:00+05:00", 1500, "cash", 225),
    ]

    assert summarize(trips).model_dump() == {
        "trips_count": 2,
        "revenue": 3900,
        "commission": 585,
        "net": 3315,
        "by_payment": {
            "cash": {"trips_count": 1, "revenue": 1500, "commission": 225, "net": 1275},
            "card": {"trips_count": 1, "revenue": 2400, "commission": 360, "net": 2040},
        },
    }
