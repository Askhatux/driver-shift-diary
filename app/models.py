"""API models: trip and daily summary."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Trip(BaseModel):
    id: str
    start: datetime
    end: datetime
    amount: int = Field(gt=0)
    payment: Literal["cash", "card"]
    commission: int = Field(ge=0)

    @model_validator(mode="after")
    def _check_trip(self) -> "Trip":
        if self.end <= self.start:
            raise ValueError("end must be later than start")
        if self.commission > self.amount:
            raise ValueError("commission must not exceed amount")
        return self


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


class Day(BaseModel):
    date: date
    summary: DaySummary
    trips: list[Trip]
