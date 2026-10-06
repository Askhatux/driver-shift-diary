import dataclasses
from datetime import timedelta, timezone

from fastapi.testclient import TestClient

from app.main import create_app


def test_client_page_is_served_at_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Дневник смен" in response.text


def test_client_page_carries_configured_day_offset(settings):
    settings = dataclasses.replace(settings, day_tz=timezone(-timedelta(hours=3, minutes=30)))

    with TestClient(create_app(settings)) as client:
        page = client.get("/").text

    assert '<meta name="day-tz-offset" content="-03:30">' in page


def test_client_assets_are_served(client):
    css = client.get("/static/app.css")
    js = client.get("/static/app.js")

    assert (css.status_code, js.status_code) == (200, 200)
    assert css.headers["content-type"].startswith("text/css")
    assert "javascript" in js.headers["content-type"]
