# FastAPI Service Template

Use this starter to create a small, independent FastAPI service. The `records` example shows the API, schema, database, migrations, and tests. Replace it with the feature requirements when you create a service. Run these commands from this directory.

## Run locally

```bash
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn chobe_service_template.main:app --reload
```

Open `/docs` for API documentation and `/health` for the health check. Each clone must set `DATABASE_URL` to its own SQLite file.

## Models and migrations

```bash
uv run alembic revision --autogenerate -m "describe schema change"
uv run alembic upgrade head
uv run alembic check
```

Review each migration before applying it. Alembic autogenerate creates a draft. Do not use `SQLModel.metadata.create_all()` when the service runs. Commit each migration with its model change, and do not edit a shared revision.

## Checks

```bash
uv run pytest -q
uv run ruff check .
```

API tests use a temporary database. Migration tests run Alembic against a temporary database. Do not use the local service database for tests.

## Clone as a new service

Copy this directory to `services/<service-name>`. Rename the `chobe_service_template` package and project, then set a unique `DATABASE_URL`. Replace `records` with the models and API for the service. Keep Pydantic 2, SQLModel, Alembic, and isolated tests. Resolve dependencies and create `uv.lock` in the new project.
