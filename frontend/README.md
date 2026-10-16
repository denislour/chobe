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

After signing in, open `/seller/shop` or choose **My shop** in the account navigation. Create your shop and edit its details.

The Django backend must be running with the shop migration applied. Public storefronts and listing management are separate features.

`pnpm run prepare` sets up a Git pre-commit hook. It runs lint and unit tests for the backend, frontend, and recommendation service before each commit. The hook uses `just`, `uv`, and `mise` with Node.js 24 and pnpm. A failed check blocks the commit.
