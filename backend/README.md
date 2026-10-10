# Chobe Backend

The backend is the Django REST API for the Chobe marketplace. It owns marketplace data and uses SQLite for local development.

## Run locally

Requirements: Python 3.14 and uv.

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver localhost:8000
```

The API documentation is available at `http://localhost:8000/api/v1/docs/`.
