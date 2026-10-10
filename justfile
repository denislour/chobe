# Start the Django API and apply local migrations.
backend:
    cd backend && uv run python manage.py migrate && uv run python manage.py runserver

# Start the Angular app with the pinned Node.js and pnpm versions.
frontend:
    cd frontend && mise exec node@24 -- pnpm install --frozen-lockfile && mise exec node@24 -- pnpm start

# Apply template migrations and start the FastAPI service.
service:
    cd services/service-template && uv run alembic upgrade head && uv run uvicorn chobe_service_template.main:app --reload

# Start the Django API, Angular app, and FastAPI template together.
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
