# Chobe Backend

This folder contains the Django API for the Chobe portfolio. Django owns marketplace data and permissions. The API uses SQLite for local development.

## Requirements

- Python 3.14
- uv

## Run locally

```bash
uv sync
cp .env.example .env
set -a
source .env
set +a
uv run python manage.py migrate
uv run python manage.py runserver
```

Open `http://127.0.0.1:8000/api/v1/docs/` for Swagger UI. The OpenAPI schema is at `/api/v1/schema/`.

The API docs use `drf-spectacular`. Its current upstream compatibility list does not include Django 6.1, so this project validates the pinned combination with local checks and tests.

## Checks

```bash
uv run python manage.py test
uv run ruff check .
```

The `accounts` app starts with a custom user model so the project can add authentication features without changing Django's user model later. User flows and API endpoints are not implemented yet.
