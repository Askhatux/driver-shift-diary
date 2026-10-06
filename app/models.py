"""API models: trip and daily summary."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, StrictInt, model_validator

INT64_MAX = 2**63 - 1  # largest INTEGER SQLite can store


def _require_string(value: object) -> object:
    # Pydantic would otherwise read a number as a unix timestamp.
    if not isinstance(value, (str, datetime)):
        raise ValueError("must be an ISO 8601 string")
    return value


def _require_offset(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timezone offset required, e.g. 2026-10-01T08:10:00+05:00")
    return value


Moment = Annotated[datetime, BeforeValidator(_require_string), AfterValidator(_require_offset)]


class Trip(BaseModel):
    id: str
    start: Moment
    end: Moment
    amount: StrictInt = Field(gt=0, le=INT64_MAX)
    payment: Literal["cash", "card"]
    commission: StrictInt = Field(ge=0, le=INT64_MAX)

    @model_validator(mode="before")
    @classmethod
    def _reject_unknown_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            unknown = sorted(set(data) - set(cls.model_fields))
            if unknown:
                raise ValueError(f"unknown field: {', '.join(unknown)}")
        return data

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
