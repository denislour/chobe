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

After signing in, open `/seller/shop` or choose **My shop** in the account navigation. Create your shop, edit its details, upload a logo or cover, and preview changes before saving. The saved preview is private to its owner. Pause or reopen the shop with confirmation; closing requires its name and is permanent.

The Django backend must be running with the shop migration applied. Public storefronts are available at `/shops/{slug}`. Guests can read active shops;
following a shop asks them to log in and returns to the same page. Signed-in users
can open `/account/followed-shops` to browse or unfollow shops, with pagination.
The storefront and following pages use the Django API and require migration
`shops/0002_shopfollow`. Hidden shops are not shown publicly.

Listing data, filters and sorting will be connected in F-011. The Listings tab
currently shows an empty state. Shop metrics, reports and follow notifications
are not included.

`pnpm run prepare` sets up a Git pre-commit hook. It runs lint and unit tests for the backend, frontend, and recommendation service before each commit. The hook uses `just`, `uv`, and `mise` with Node.js 24 and pnpm. A failed check blocks the commit.
