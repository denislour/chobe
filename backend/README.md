# Chobe Backend

The backend is the Django REST API for the Chobe marketplace. It owns marketplace data and uses SQLite for local development.

## Cache storage

Django uses `DatabaseCache` in a separate `cache.sqlite3` file. The cache connection enables WAL with `synchronous=NORMAL`; business data, sessions and task records stay in `db.sqlite3`. All web processes must share the same local cache file. Set `DJANGO_CACHE_DB_PATH` to change its path; its parent directory must exist. Do not use a network filesystem or point the cache path at the business database.

All API throttles inherit DRF's default cache, so IP, account and user limits share this SQLite storage. Cache writes use `IMMEDIATE` transactions to avoid deferred read-to-write lock upgrades. The cache holds up to about 10,000 entries before culling, instead of Django's default 300; culling can still remove active throttle keys when capacity is exceeded. Session responses stay uncached so revocation and deletion use current database values. There are no public listing or search queries to cache yet.

Run `uv run python manage.py createcachetable --database cache` once before starting the server. SQLite still allows only one writer, and DRF throttles are not atomic security limits. For multi-host deployment, use a shared cache service or another rate limiter.

## Run locally

Requirements: Python 3.14 and uv.

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createcachetable --database cache
uv run python manage.py seed_demo_admin
uv run python manage.py runserver localhost:8000
```

The API documentation is available at `http://localhost:8000/api/v1/docs/`.

The Django Unfold admin is available at `http://localhost:8000/admin/`. The demo account is `admin` with password `abc123ABC!!!`.
