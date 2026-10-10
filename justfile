set positional-arguments

# Start the Django API and apply local migrations.
backend:
    @just be

# Start the Angular app with the pinned Node.js and pnpm versions.
frontend:
    @just fe

# Start the Django API and Angular app together.
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    set -m
    just be &
    backend_pid=$!
    just fe &
    frontend_pid=$!
    trap 'kill -- "-$backend_pid" "-$frontend_pid" 2>/dev/null || true' EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    wait -n "$backend_pid" "$frontend_pid"

# Run, test, migrate, or lint the product recommendation service.
service action="run":
    #!/usr/bin/env bash
    set -euo pipefail
    cd services/product_recommendation
    case "$1" in
        run) uv run alembic upgrade head; uv run uvicorn product_recommendation.main:app --reload --host localhost --port 8001 ;;
        test) uv run python -m pytest -q ;;
        migrate) uv run alembic upgrade head ;;
        lint) uv run ruff check .; uv run ruff format --check . ;;
        *) echo "Unknown service command: $1. Use run, test, migrate, or lint." >&2; exit 1 ;;
    esac

# Run, test, migrate, or lint the Django backend.
be action="run":
    #!/usr/bin/env bash
    set -euo pipefail
    cd backend
    case "$1" in
        run) uv run python manage.py migrate; uv run python manage.py runserver localhost:8000 ;;
        test) uv run python manage.py test ;;
        migrate) uv run python manage.py migrate ;;
        lint) uv run ruff check .; uv run ruff format --check . ;;
        *) echo "Unknown backend command: $1. Use run, test, migrate, or lint." >&2; exit 1 ;;
    esac

# Run, test, or lint Angular; migrate reports that no database migration is needed.
fe action="run":
    #!/usr/bin/env bash
    set -euo pipefail
    cd frontend
    case "$1" in
        run) mise exec node@24 -- pnpm install --frozen-lockfile; mise exec node@24 -- pnpm start ;;
        test) mise exec node@24 -- pnpm test --watch=false ;;
        migrate) echo "Angular has no database migrations. Use just be migrate or just service migrate." ;;
        lint) mise exec node@24 -- pnpm lint ;;
        *) echo "Unknown frontend command: $1. Use run, test, migrate, or lint." >&2; exit 1 ;;
    esac

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
