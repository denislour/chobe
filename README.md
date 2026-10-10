# Chobe

Chobe is a portfolio project for a Vietnamese marketplace. It shows a small system built with Django, Angular, and FastAPI services.

## Project folders

- `backend/` contains the initialized Django API. See its README to run it.
- `frontend/` contains the initialized Angular web app. See its README to run it.
- `services/` contains independent FastAPI projects. Each service has its own setup, README, and database. `service-template/` is a starter for future services; recommendation features are not implemented yet.

Each initialized project folder has its own README and `.gitignore`. Project notes and agent instructions are kept locally in `docs/` and `.pi/` and are not part of this repository.

## Run locally

Install `just`, `uv`, `mise`, and Node.js 24. Then start all three apps with:

```bash
just all
```

Run one app with `just backend`, `just frontend`, or `just service`. The Angular project uses pnpm, pinned in `frontend/package.json`.

## Status

The Django backend and Angular frontend are initialized. The FastAPI service template is ready to copy for future services.
