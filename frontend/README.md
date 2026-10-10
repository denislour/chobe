# Chobe Frontend

The frontend is the Angular web app for the Chobe marketplace. It uses Node.js 24 LTS and pnpm.

## Run locally

```bash
npm install --global --allow-scripts=pnpm pnpm@12.11.2
pnpm install
pnpm run prepare
pnpm start
```

Open `http://localhost:4200/` to view the app.

`pnpm run prepare` sets up a Git pre-commit hook. It runs lint and unit tests for the backend, frontend, and recommendation service before each commit. The hook uses `just`, `uv`, and `mise` with Node.js 24 and pnpm. A failed check blocks the commit.
