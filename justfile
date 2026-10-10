# Start the Django API and apply local migrations.
backend:
    cd backend && uv run python manage.py migrate && uv run python manage.py runserver localhost:8000

# Start the Angular app with the pinned Node.js and pnpm versions.
frontend:
    cd frontend && mise exec node@24 -- pnpm install --frozen-lockfile && mise exec node@24 -- pnpm start

# Apply migrations and start the product recommendation service.
service:
    cd services/product_recommendation && uv run alembic upgrade head && uv run uvicorn product_recommendation.main:app --reload --host localhost --port 8001

# Start the Django API, Angular app, and recommendation service together.
all:
    #!/usr/bin/env bash
    set -e
    just backend &
    backend_pid=$!
    just frontend &
    frontend_pid=$!
    just service &
    service_pid=$!
    trap 'kill "$backend_pid" "$frontend_pid" "$service_pid" 2>/dev/null || true' INT TERM
    wait
