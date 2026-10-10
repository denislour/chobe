# Product Recommendation Service

An independent FastAPI service for future product recommendations in the Chobe marketplace. This project is copied from the shared service starter and currently contains its sample records API; recommendation behavior is not implemented yet.

## Run locally

Requirements: Python 3.14 and uv.

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn product_recommendation.main:app --reload --host localhost --port 8001
```

Open `http://localhost:8001/docs/` for the API documentation.
