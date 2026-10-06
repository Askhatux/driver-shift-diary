"""Daily summary calculation."""

from app.models import ByPayment, DaySummary, Totals, Trip


def _totals(trips: list[Trip]) -> Totals:
    revenue = sum(t.amount for t in trips)
    commission = sum(t.commission for t in trips)
    return Totals(
        trips_count=len(trips),
        revenue=revenue,
        commission=commission,
        net=revenue - commission,
    )


def summarize(trips: list[Trip]) -> DaySummary:
    """Totals for the given trips, overall and split by payment method."""
    return DaySummary(
        **_totals(trips).model_dump(),
        by_payment=ByPayment(
            cash=_totals([t for t in trips if t.payment == "cash"]),
            card=_totals([t for t in trips if t.payment == "card"]),
        ),
    )
