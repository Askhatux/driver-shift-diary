"""Load the trips file at startup through the same model and save function as POST."""

import json
import sqlite3
from pathlib import Path

from app import db
from app.models import Trip


def load_trips_file(conn: sqlite3.Connection, path: Path) -> None:
    if not path.exists():
        return
    for record in json.loads(path.read_text(encoding="utf-8")):
        db.save_trip(conn, Trip.model_validate(record))
