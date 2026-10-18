# Chobe Backend

The backend is the Django REST API for the Chobe marketplace. It owns marketplace data and uses SQLite for local development.

The `accounts` Django app contains authentication, profiles and privacy features. Views, serializers and schemas handle the API; services handle multi-step changes and transactions. Background jobs live in `accounts/tasks/`. Dependencies are managed in one `pyproject.toml` and `uv.lock`.

All business API views inherit directly from `ModelViewSet` and use DRF's
`SimpleRouter`. Standard operations use DRF actions; additional operations use
`@action`. Each view blocks inherited operations outside its API contract.
There are no custom routers or routing attributes. Django admin, schema/docs
and the root redirect use normal Django URL patterns.

The current user's profile uses `GET/PATCH /api/v1/profiles/me/`, with its avatar
at `GET /api/v1/profiles/me/avatar/`. Privacy settings use
`GET/PATCH /api/v1/privacy-settings/me/`. The current shop uses
`GET /api/v1/shops/mine/`. Viewing history uses
`GET/POST /api/v1/me/viewing-history/` and
`DELETE /api/v1/me/viewing-history/clear/`.

The `backoffice` app owns Unfold configuration, the admin login form and throttles, themed User/Group admin classes and admin UI tests. Put future admin template overrides in `backoffice/templates/admin/` and theme assets in `backoffice/static/backoffice/`. It is installed before `unfold` so its templates take priority. Account model registration and account data permissions stay in `accounts/admin.py`; import themed admin classes from `backoffice.admin` there.

## Shop management

The `shops` app provides owner-only creation, editing, status changes, image uploads and previews. Each user can own one shop. Updates require the current `version`; stale updates return 409. Closed shops cannot be reopened. Admins can suspend and restore shops through audited admin actions.

Apply the `shops/0001_initial` migration before using these endpoints. Shop images are stored as JPEG bytes in SQLite; uploads allow JPEG, PNG and WebP up to 2 MiB per image. Configure an overall request body limit in the production proxy as well. Account exports include shop data, and account deletion removes the shop and its images.

## Public storefronts and following

Apply `shops/0002_shopfollow` before using following. Public storefronts use
`GET /api/v1/shop-storefronts/{slug}/`; public images use
`GET /api/v1/shop-storefronts/{slug}/images/{logo|banner}/`. Only active shops with
active owners are public. Old slugs redirect to the current storefront API.
Storefronts have a separate prefix from owner operations, so UUID-shaped slugs do not conflict with shop IDs.

Authenticated users can `PUT` or `DELETE /api/v1/me/followed-shops/{uuid}/`
with CSRF protection. Both operations are idempotent and return 204.
`GET /api/v1/me/followed-shops/` is private and paginated (20 per page, up to 50
with `page_size`). Hidden shops stay followed but do not appear in this list.
Account exports include follow records; account or shop deletion removes related follows.

Public responses and images are not cached. Public reads share a limit of 120
requests per minute per IP; follow changes use the account mutation limit.
There is no listing model yet. Storefront listing data, filters and sorting will
be connected in F-011. No listing API is exposed by this feature.

## Categories and attribute schemas

Apply `categories/0001_initial` before using taxonomy. Public category browsing is
available at `GET /api/v1/categories/`, with a published schema at
`GET /api/v1/categories/{uuid}/` and filter definitions at the `facets/` action.
`POST .../validate-attributes/` checks a schema version and typed values without
saving a listing. Unknown fields, invalid values and outdated versions are rejected.

Manage categories in the Angular workspace at `/admin/categories`. The Django
admin's category lists link to this workspace and remain read-only. Staff need
`categories.view_category` plus `add_category` or `change_category` to edit;
`publish_category` and `retire_category` are separate permissions. All management
writes require CSRF and the current draft version. The API uses
`/api/v1/admin/categories/`, including `publish/`, `retire/`, `revisions/`,
`history/` and `capabilities/` actions.

Draft edits leave the published snapshot unchanged. Publication records an
immutable revision and an audit event in the same transaction. Restoring an old
version creates a new draft through the editor. Category addresses stay fixed
after first publication; attribute keys keep their type and unit across versions.
Trees allow four levels. Publish parents first and retire or move active children
before retiring their parent. Restricted categories cannot be published.

Demo taxonomy is available through `seed_demo_categories`. Run `seed_demo_accounts`
first to create the default `demo_catalog` editor, or pass `--username` with an
existing active staff user who has taxonomy permissions. Existing categories are
preserved; reserved demo slugs owned by unrelated records stop the seed.

Listings, search results and search/moderation consumers are not available yet.
Published revisions and audit events are retained for those integrations; no jobs
are sent to services that do not exist. F-011 will reuse the attribute validator
when saving listings, and F-021 will use category facets for search.

## Cache storage

Django uses `DatabaseCache` in a separate `cache.sqlite3` file. The cache connection enables WAL with `synchronous=NORMAL`; business data, sessions and task records stay in `db.sqlite3`. All web processes must share the same local cache file. Set `DJANGO_CACHE_DB_PATH` to change its path; its parent directory must exist. Do not use a network filesystem or point the cache path at the business database.

All API throttles inherit DRF's default cache, so IP, account and user limits share this SQLite storage. Admin login also uses this cache with separate limits of 20 attempts/minute/IP and 5 attempts/minute/username; rejected attempts show a form error. Cache writes use `IMMEDIATE` transactions to avoid deferred read-to-write lock upgrades. The cache holds up to about 10,000 entries before culling, instead of Django's default 300; culling can still remove active throttle keys when capacity is exceeded. Session, profile, consent, history and export responses stay uncached so revocation and deletion use current database values. There are no public listing or search queries to cache yet.

Run `uv run python manage.py createcachetable --database cache` once before starting the server. SQLite still allows only one writer, and DRF throttles are not atomic security limits. For multi-host deployment, use a shared cache service or another rate limiter.

## Background jobs

Huey 3.4.0 uses a separate `queue.sqlite3` file with WAL and full synchronous writes. Run `uv run python manage.py run_huey` or `just worker`. The consumer uses two worker threads and an internal scheduler; Redis and Celery Beat are not required. Set `DJANGO_QUEUE_DB_PATH` to change the queue path. Keep business, cache and queue paths separate and on the same local host.

Business tasks keep the `django.tasks` API. `OutboxHueyBackend` writes `DBTaskResult` in the business transaction, then publishes only its UUID to Huey after commit. The existing `django-tasks-db` dependency now provides the outbox and task status, not the main execution worker. Do not run `db_worker` alongside Huey. Existing READY jobs remain usable without changing task IDs or paths.

`tasks/backend.py` calls the shared `tasks.dispatch` dispatcher. The `tasks` app registers execution, startup recovery, periodic dispatch and finished-result cleanup without importing account code. Each business app owns its task functions; execution resolves them from the outbox `task_path`. Account retention and session cleanup stay in `accounts/tasks/dispatch.py`. The shared execution and dispatch tasks retain their old serialized Huey identifiers so messages already in the queue remain readable after this move. Restart both web and worker processes together after updating the code.

A startup scan and a minute-level periodic scan recover READY jobs if queue publication or delivery was lost. Duplicate delivery is guarded by a short database claim. Failed business tasks are not retried automatically; interrupted RUNNING tasks require review before requeueing because side effects such as email cannot be guaranteed exactly once.

At 03:00 UTC each day, Huey cleans expired account data and sessions, and prunes finished outbox results older than 14 days. Keep only one periodic scheduler enabled; additional consumers must use `--no-periodic`. A stopped scheduler does not replay every missed daily run. Use graceful shutdown and monitor the outbox backlog. See `docs/plan/25-huey-va-outbox.md` for the full contract.

## Run locally

Requirements: Python 3.14 and uv.

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createcachetable --database cache
export DJANGO_DEMO_MODE=true
uv run python manage.py seed_demo_accounts --admin-only
uv run python manage.py runserver localhost:8000
```

Run `just emails` from the repository root to build email templates. Run `just worker` in another terminal to process background jobs. After changing task paths, apply migrations and restart both the server and worker.

The API documentation is available at `http://localhost:8000/api/v1/docs/`.

The Django Unfold admin is available at `http://localhost:8000/admin/`. With `DJANGO_DEMO_MODE=true`, the demo account is `admin` with password `abc123ABC!!!`, and the login page shows demo placeholders. Demo mode is disabled by default. Disabling it hides the placeholders and blocks seeding; it does not remove an existing demo account.

## Listings and marketplace

The `listings` app provides private drafts, local image processing and immutable
submitted snapshots. `discovery` owns public queries, `engagement` owns favorites,
shop follows and saved searches, `moderation` owns reviews and reports, and
`notifications` owns preferences, inbox and delivery. Cross-app transactions live
in `workflows`; shared technical code lives in `common`. Seller APIs live at
`/api/v1/me/listings/`; public discovery uses `/api/v1/home/` and
`/api/v1/listings/`. All routes use the native DRF SimpleRouter.

Review submissions at the frontend `/admin/moderation` workspace. Active staff
need `listings.moderate_listing`. They can approve, reject, review appeals and
approve a previously rejected current snapshot. Decisions retain their actor,
reason and source. Automatic moderation and FastAPI integration are deferred;
there is no service dependency or simulated AI job. Editing a draft leaves its
last approved snapshot public until hidden, sold, removed or otherwise ineligible.

Images accept JPEG, PNG and WebP up to 5 MiB, 8192 pixels per side and 24 million
pixels total; they are converted to metadata-free JPEGs up to 1920 pixels.
Listings allow 10 attached images, with the first as cover. Draft and moderation
image endpoints enforce ownership or staff permission. Public images must belong
to the approved snapshot.

SQLite FTS5 indexes only published snapshots using unicode61 with diacritic
removal and Vietnamese d normalization. Search validates category, area, price,
condition and typed category filters. Every public query checks current shop,
account, category, status and activity deadline.

Private APIs also support favorites, saved searches, notification preferences,
inbox and reports. Inbox and email require explicit opt-in. Saved-search matching
and email run through Huey/outbox tasks, with deduplication and delivery-time
consent checks. Daily matching runs at 04:00 UTC; listing maintenance runs at
03:15 UTC and notification cleanup runs at 03:30 UTC. The existing native Huey
daily task name is retained so stored retries can still execute.
No workers are started by installing the app. Use the existing `run_huey` command.

Eligible owner actions renew a six-calendar-month deadline. Views, contacts,
admin decisions and background processing do not renew it. Maintenance erases
expired listing content, images and revisions, retaining a deleted record and
minimal audit; deletion cannot be undone. Public queries hide expired listings
before maintenance runs. Development data is not migrated, seeded or cleaned
as part of implementation.

Reports require login. Staff need `moderation.review_report`; hiding a listing also
requires `listings.moderate_listing`, and suspending a shop requires
`shops.change_shop`. Internal reasons and reporter identity are not public.

Apply the full migration graph before running this source. The new ownership
migrations keep existing table names, data IDs, permission grants and queued
outbox arguments; they move model state, content types and notification task paths.
Stop the web app and worker, back up the business database, run
`uv run python manage.py migrate`, then restart both with the new source.
Do not migrate only an intermediate app, fake migrations or reset the database.
These migrations have not been applied or tested as part of this refactor.

## Demo seed data

Each app owns a standard Django command directly under `management/commands/`.
The seed file contains its fixtures, helper functions and `Command` class;
`manage.py` discovers it without a loader or manual Python imports.

| App | Seed file | Clear file |
| --- | --- | --- |
| accounts | `seed_demo_accounts.py` | `clear_seed_demo_accounts.py` |
| categories | `seed_demo_categories.py` | `clear_seed_demo_categories.py` |
| shops | `seed_demo_shops.py` | `clear_seed_demo_shops.py` |
| listings | `seed_demo_listings.py` | `clear_seed_demo_listings.py` |

After migrations, run these shortcuts from the repository root:

```bash
just seed demo data
just clear seed demo data
```

The recipes enable demo mode for their commands. Seed runs accounts, categories,
shops and listings; clear reverses that order. Both stop on the first error and
do not run migrations, tests or workers. Earlier commands remain committed if a
later command fails, since each command owns its transaction.

After migrations, run from `backend/` in dependency order:

```bash
export DJANGO_DEMO_MODE=true
uv run python manage.py seed_demo_accounts
uv run python manage.py seed_demo_categories
uv run python manage.py seed_demo_shops
uv run python manage.py seed_demo_listings
```

Accounts include 10 sellers, 5 buyer-only users, 3 staff with separate permissions
and 3 inactive accounts. Categories include public, draft, restricted and retired
scenarios. Shops include follows and all four statuses. Listings include 100 item
scenarios, image/review snapshots, moderation, appeals, audit, favorites, history,
saved searches, notifications, reports and metrics. Each command reads its
prerequisites and reports missing data; it does not run another app's seed.

`seed_demo_accounts --admin-only` creates or updates the separate bootstrap demo
superuser. `seed_demo_categories --username <editor>` chooses another staff editor.
`seed_demo_listings --guide <path>` selects the output guide path, defaulting to
`../docs/DEMO_DATA.md`. The guide describes accounts, credentials and review journeys.

To clear the demo, reverse the dependency order:

```bash
uv run python manage.py clear_seed_demo_listings
uv run python manage.py clear_seed_demo_shops
uv run python manage.py clear_seed_demo_categories
uv run python manage.py clear_seed_demo_accounts
```

All seed and clear commands require demo mode and use transactions. Clear selects
reserved records by stable IDs plus demo ownership/markers. Accounts with shops,
shops with listings, and categories referenced by listings or non-demo children
are preserved with an error. Referencing rows such as follows and favorites of
removed demo entities are removed with those entities. Shared taxonomy and the
bootstrap admin are preserved. No command flushes the database or automatically
backs it up, and there is no transaction spanning all four commands.

Existing demo edits and passwords survive seeding. Clear removes matching demo
records, including their edits; a following seed can rebuild them. Reserved demo
usernames use `@demo.chobe.invalid`, child-category/shop slugs use `demo-`, and
listing IDs 1101–2010 belong to the dataset. Records outside that identity are
preserved; namespace conflicts stop seeding.

Email delivery states such as `sent` are fixtures, not proof of delivery. Seeds
do not send email/SMS, call AI, enqueue jobs or start workers. Runtime services
continue to handle real validation, image processing and publication. Photos
remain in `listings/fixtures/demo/`, with source URLs in `SOURCES.json`.
