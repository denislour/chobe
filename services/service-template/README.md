# FastAPI Service Template

A starter project for independent Chobe services. It includes a small records API, SQLite storage, Alembic migrations, and API documentation.

## Run locally

Requirements: Python 3.14 and uv.

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn chobe_service_template.main:app --reload
```

Open `http://127.0.0.1:8000/docs/` for the API documentation.
