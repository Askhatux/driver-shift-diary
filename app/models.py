"""API models: trip and daily summary."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Trip(BaseModel):
    id: str
    start: datetime
    end: datetime
    amount: int
    payment: Literal["cash", "card"]
    commission: int


class Totals(BaseModel):
    trips_count: int
    revenue: int
    commission: int
    net: int  # "на руки" = revenue - commission


class ByPayment(BaseModel):
    cash: Totals
    card: Totals


class DaySummary(Totals):
    by_payment: ByPayment
