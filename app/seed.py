"""Load the trips file at startup through the same model and save function as POST."""

import json
import logging
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from app import db
from app.models import Trip

logger = logging.getLogger(__name__)


def _label(record: object, number: int) -> str:
    if isinstance(record, dict) and isinstance(record.get("id"), str):
        return record["id"]
    return f"#{number}"


def _reason(error: ValidationError) -> str:
    return "; ".join(
        ": ".join([*map(str, e["loc"]), e["msg"]]) for e in error.errors(include_url=False)
    )


def load_trips_file(conn: sqlite3.Connection, path: Path) -> None:
    """Save every valid trip; skip bad ones and log a one-line report."""
    if not path.exists():
        logger.warning("trips file %s not found, starting without it", path)
        return
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        logger.error("cannot read trips file %s: %s", path, error)
        return
    if not isinstance(records, list):
        logger.error("trips file %s must contain a JSON array", path)
        return
    added, unchanged, rejected = 0, 0, []
    for number, record in enumerate(records, start=1):
        try:
            _, created = db.save_trip(conn, Trip.model_validate(record))
        except ValidationError as error:
            rejected.append(f"{_label(record, number)}: {_reason(error)}")
            continue
        except db.TripConflict as error:
            rejected.append(str(error))
            continue
        if created:
            added += 1
        else:
            unchanged += 1
    report = f"trips file {path}: added {added}, unchanged {unchanged}, rejected {len(rejected)}"
    logger.info("; ".join([report, *rejected]))
