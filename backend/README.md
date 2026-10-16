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
uv run python manage.py seed_demo_admin
uv run python manage.py runserver localhost:8000
```

Run `just emails` from the repository root to build email templates. Run `just worker` in another terminal to process background jobs. After changing task paths, apply migrations and restart both the server and worker.

The API documentation is available at `http://localhost:8000/api/v1/docs/`.

The Django Unfold admin is available at `http://localhost:8000/admin/`. With `DJANGO_DEMO_MODE=true`, the demo account is `admin` with password `abc123ABC!!!`, and the login page shows demo placeholders. Demo mode is disabled by default. Disabling it hides the placeholders and blocks seeding; it does not remove an existing demo account.
