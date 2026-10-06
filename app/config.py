"""Settings read from environment variables."""

import os
import re
from dataclasses import dataclass
from datetime import timedelta, timezone
from pathlib import Path

_OFFSET_RE = re.compile(r"([+-])([0-9]{2}):([0-9]{2})")


@dataclass(frozen=True)
class Settings:
    day_tz: timezone  # fixed offset in which a "day" is counted
    trips_file: Path  # JSON file loaded at startup
    db_path: Path  # SQLite database file


def parse_offset(value: str) -> timezone:
    """Parse a strict ±HH:MM offset into a fixed-offset timezone."""
    match = _OFFSET_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"DAY_TZ_OFFSET must look like +05:00, got {value!r}")
    sign, hours, minutes = match.groups()
    if int(hours) > 23 or int(minutes) > 59:
        raise ValueError(f"DAY_TZ_OFFSET is out of range: {value!r}")
    delta = timedelta(hours=int(hours), minutes=int(minutes))
    return timezone(-delta if sign == "-" else delta)


def load_settings() -> Settings:
    """Read settings; raises ValueError on a bad value so the server does not start."""
    return Settings(
        day_tz=parse_offset(os.environ.get("DAY_TZ_OFFSET", "+05:00")),
        trips_file=Path(os.environ.get("TRIPS_FILE", "data/trips.json")),
        db_path=Path(os.environ.get("DB_PATH", "data/trips.db")),
    )
