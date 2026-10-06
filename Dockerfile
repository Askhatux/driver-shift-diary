FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /bin/uv

WORKDIR /app

# Dependencies first, so code changes do not reinstall them. Use the image's Python 3.12.
COPY pyproject.toml uv.lock .python-version ./
RUN UV_PYTHON_DOWNLOADS=never uv sync --frozen --no-dev --no-install-project

# Database directory; docker-compose mounts a volume here.
RUN mkdir -p /data

COPY app ./app
COPY static ./static
COPY data/trips.json data/demo-trips.json ./data/

ENV PATH="/app/.venv/bin:$PATH" \
    DB_PATH=/data/trips.db \
    TRIPS_FILE=/app/data/demo-trips.json \
    DAY_TZ_OFFSET=+05:00

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
