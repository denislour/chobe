# Chobe Frontend

This folder contains the Angular web app for the Chobe portfolio. It uses Angular 21 and Node.js 24 LTS.

Use the Node.js version in `.node-version`. The required pnpm version is pinned in `package.json`.

## Run locally

```bash
pnpm install
pnpm start
```

Open `http://localhost:4200/`. The app will reload when source files change.

## Checks

```bash
pnpm exec ng test --watch=false
pnpm build
```

Use `pnpm exec ng generate` to add Angular files. Keep the app small until a feature is ready to build.
