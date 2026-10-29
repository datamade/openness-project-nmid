# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Money Trail NM — a Django-based campaign finance transparency site for New Mexico. It ingests CSV data from the NM Secretary of State CFIS API (via a separate scraper repo), loads it into PostgreSQL, and exposes it via Django views and a Django REST Framework API.

## Development Commands

**Start the app:**
```bash
docker-compose up
```

**Run tests:**
```bash
docker compose -f docker-compose.yml -f camp_fin/tests/docker-compose.yml run --rm app
```

**Run a management command:**
```bash
docker-compose run --rm app python manage.py <command>
```

**Run migrations / collect static:**
```bash
docker-compose run --rm app python manage.py migrate
docker-compose run --rm app python manage.py collectstatic
```

**Build search index (required after bulk data imports):**
```bash
docker-compose run --rm app python manage.py make_search_index
```

## Data Import Pipeline

Data flows: S3 CSVs → management commands → PostgreSQL → search index.

The `Makefile` orchestrates imports:
- `make nightly` — import candidates, PACs, and all transactions for the current year
- `make quarterly` — import transactions from 2020 to current year
- `make import/candidates`, `make import/pacs` — committee data only
- `make import/CON_<month>_<year>`, `make import/EXP_<month>_<year>` — transactions

The GitHub Actions workflow `etl.yml` runs nightly imports in parallel across 12 months for CON and EXP transaction types.

Key management commands (all under `camp_fin/management/commands/`):
- `import_candidates` / `import_pac_committees` — committee records
- `import_candidate_filings` / `import_pac_filings` — filing records
- `import_transactions --transaction-type CON/EXP --months <m> --year <y> --file <path>`
- `flush_camp_fin` — wipe all campaign finance data (destructive)
- `clear_cache` — clear Django cache

## Architecture

**Main app:** `camp_fin/` — models, views, serializers, templates, management commands, tests.

**CMS app:** `pages/` — editable pages (About, Financial Disclosures, Lobbyists, Donations) managed via Django admin with CKEditor.

**Key models** (47 total in `camp_fin/models.py`):
- `Candidate`, `PAC` — core political entities
- `Campaign` — a candidate's campaign record; each candidate may have multiple
- `Transaction` — contributions (CON) and expenditures (EXP)
- `Filing` / `FilingPeriod` — financial filing windows
- `Organization` — employers/donors making contributions
- `Lobbyist` / `LobbyistTransaction` — lobbyist activity
- `Entity` — polymorphic wrapper used for merging candidates/PACs

**API:** Django REST Framework endpoints under `/api/`. Most support CSV export via `?format=csv`. Defined in `camp_fin/api.py` (serializers) and `camp_fin/views.py`.

**Search:** Custom full-text search index built by `make_search_index`; the `/search/` route and `/api/search/` use it.

**Admin features:** `merge_objects.py` provides an admin interface to merge duplicate candidate/PAC records. Entity slugs are generated on save.

**Caching:** Controlled by `DJANGO_CACHE_BACKEND` env var. Defaults to dummy cache in dev; use `django.core.cache.backends.db.DatabaseCache` in production to enable select2 autocomplete persistence.

**Settings:** `camp_fin/settings.py`. Sentry is integrated with 5% tracing rate, skipping static asset requests.

## Testing Conventions

Tests live in `camp_fin/tests/`. Use the `FakeTestData` mixin (defined in the test helpers) to generate fixture data — don't write raw SQL or fixtures. Use `django.test.TestCase` for most tests and `TransactionTestCase` when testing rollback behavior.
