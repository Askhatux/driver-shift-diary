"""API models: trip and daily summary."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, StrictInt, model_validator

INT64_MAX = 2**63 - 1  # largest INTEGER SQLite can store


class Trip(BaseModel):
    id: str
    start: datetime
    end: datetime
    amount: StrictInt = Field(gt=0, le=INT64_MAX)
    payment: Literal["cash", "card"]
    commission: StrictInt = Field(ge=0, le=INT64_MAX)

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
