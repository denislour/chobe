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

## Categories

Public routes `/categories` and `/categories/:id` show published categories,
subcategories, dynamic attribute fields and available filter definitions. The
attribute check validates against the displayed schema version without saving a
listing. Changing or reloading a category asks before discarding entered values.

The authenticated `/admin/categories` workspace uses Django permissions. It
supports draft editing, attribute form/filter previews, publication and retirement
confirmation, version conflicts, audit history and copying an old published
version into a new draft. The Django admin links to this workspace. No admin
permissions are inferred from a username or from the route guard.

Apply the backend category migration first. The optional backend demo seed can
populate sample categories. Listing results and the listing editor will be
connected in later features; this feature shows their empty states.

## Marketplace routes

- `/`: published categories and recent listings, with independent section retries.
- `/search`: URL-based keywords, filters, sorting, pagination and saved searches.
- `/listings/:id`: approved photos, details, current phone consent and contact actions.
- `/seller/listings`: private dashboard, status actions, renewal, deletion and CSV.
- `/seller/listings/new`, `/seller/listings/:id/edit`: draft editor, image management,
  preview, manual-review submission, reasons and appeals.
- `/admin/moderation`: permission-checked manual approval, rejection and re-review.
- `/saved`: favorites and consent-controlled viewing history.
- `/alerts`: saved searches, inbox and explicit email/inbox preferences.
- `/compare`: up to three compatible public listings; IDs remain in the URL/memory.
- `/reports`, `/admin/reports`: private report status and staff review actions.

Angular calls Django only. Automatic moderation and FastAPI services are planned
for a later phase. Draft changes are separate from approved public snapshots;
forms retain input on errors and require a reload after version conflicts.
