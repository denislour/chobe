set positional-arguments

# Start the Django API and apply local migrations.
backend:
    @just be

# Start the Angular app with the pinned Node.js and pnpm versions.
frontend:
    @just fe

# Set up and start Django, Angular, Mailpit, and the email worker.
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    set -m
    just emails
    just mailpit-setup
    just be migrate
    pids=()
    trap 'for pid in "${pids[@]}"; do kill -- "-$pid" 2>/dev/null || true; done' EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    just mailpit &
    pids+=($!)
    for attempt in {1..40}; do
        if curl --silent --fail http://localhost:8025/readyz >/dev/null; then break; fi
        sleep 0.25
    done
    curl --silent --show-error --fail http://localhost:8025/readyz >/dev/null
    just worker &
    pids+=($!)
    just be &
    pids+=($!)
    just fe &
    pids+=($!)
    wait -n "${pids[@]}"

# Download the pinned Mailpit binary and verify its checksum.
mailpit-setup:
    cd backend && uv run python scripts/install_mailpit.py

# Open the local inbox at http://localhost:8025; SMTP uses localhost:1025.
mailpit: mailpit-setup
    backend/.tools/mailpit/v1.31.5/mailpit --listen localhost:8025 --smtp localhost:1025 --database backend/.tools/mailpit/inbox.sqlite3

# Run Huey execution and periodic scheduling in one process.
worker:
    cd backend && uv run python manage.py run_huey

# Compile MJML to Django HTML templates before starting or packaging the backend.
emails:
    cd backend && mise exec node@24 -- pnpm install --frozen-lockfile
    cd backend && mise exec node@24 -- pnpm run build:emails

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

# Run, test, migrate, lint, or clean up expired Django account data.
be action="run":
    #!/usr/bin/env bash
    set -euo pipefail
    cd backend
    case "$1" in
        run) just emails; uv run python manage.py migrate; uv run python manage.py createcachetable --database cache; uv run python manage.py runserver localhost:8000 ;;
        test) just emails; uv run python manage.py test ;;
        migrate) uv run python manage.py migrate; uv run python manage.py createcachetable --database cache ;;
        cleanup) uv run python manage.py cleanup_account_data ;;
        lint) uv run ruff check .; uv run ruff format --check . ;;
        *) echo "Unknown backend command: $1. Use run, test, migrate, cleanup, or lint." >&2; exit 1 ;;
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
