# Project Audit — Job Application Tracker

Audit date: 2026-10-11. Baseline: `main` at `b669547`. Changes are on the `interview-demo` branch.

## Architecture

A single-process, server-rendered web app:

```text
Browser ──HTTP──> Uvicorn (ASGI server) ──> FastAPI app (app.py)
                                             ├─ route functions (GET/POST)
                                             ├─ validate_application_form()
                                             ├─ sqlite3 with ? placeholders ──> jobs.db
                                             └─ Jinja2 templates (+ Bootstrap 5 CDN) ──> HTML response
```

There is no JavaScript framework and no JSON API: every action is an HTML form that
POSTs to the server, which validates, writes to SQLite and answers with a
`303 See Other` redirect (Post/Redirect/Get), or re-renders the form with errors.

## Source Structure

| File | Purpose |
| --- | --- |
| `app.py` | Whole backend: app setup, DB helpers, validation, 6 routes, error handlers |
| `templates/base.html` | Layout, navbar, Bootstrap CDN, alert messages, demo banner |
| `templates/index.html` | List page: search/filter form, table with status badges, empty state |
| `templates/add_job.html`, `edit_job.html` | Forms that redisplay entered values on error |
| `templates/404.html`, `500.html` | Custom error pages |
| `static/style.css` | Status badge colours and small layout tweaks |
| `tests/test_app.py` | Original Pytest suite (10 tests) |
| `tests/test_additional_coverage.py` | Added on `interview-demo` (21 test cases) |

## Key Functions in app.py

| Function | Role |
| --- | --- |
| `get_db_connection()` | Opens `sqlite3.connect(DATABASE)` with `row_factory = sqlite3.Row` |
| `init_db()` | `CREATE TABLE IF NOT EXISTS applications (...)` at import time |
| `validate_application_form(form)` | Strips input, returns `(data, errors)`; checks required fields, status whitelist, `%Y-%m-%d` date, http/https URL with a host |
| `get_application_or_404(id)` | Parameterized `SELECT`; raises `HTTPException(404)` if missing |
| `redirect_with_message()` | 303 redirect with `message`/`category` query parameters |
| `index()` | Builds `WHERE` from optional search (`LIKE` on company/role) and status; `ORDER BY created_at DESC, id DESC` |
| `create_job()`, `update_job()`, `delete_job()` | Parameterized `INSERT`/`UPDATE`/`DELETE` |

## Dependencies

`fastapi 0.116.1`, `uvicorn 0.35.0`, `jinja2 3.1.6`, `python-multipart 0.0.20` (needed for
`request.form()`), `httpx 0.28.1` (needed by `TestClient`), `pytest 8.4.2`. Bootstrap 5.3.3
is loaded from the jsDelivr CDN.

## Baseline Results (before any change)

- `python -m pytest`: **10 passed**.
- All CRUD, search, filter and validation flows worked locally.

## Defects Found and Fixed

| # | Problem | Impact | Fix (commit `a24a5c8`) |
| --- | --- | --- | --- |
| 1 | `@app.exception_handler(500)` is only used by Starlette for *unhandled* exceptions. The app raises `HTTPException(status_code=500)`, which went to FastAPI's default handler and returned `{"detail":"Internal Server Error"}` JSON | Custom 500 page never shown | One `StarletteHTTPException` handler renders 404.html/500.html; other codes keep FastAPI's default |
| 2 | `/edit/abc` returned FastAPI's 422 JSON validation error | Inconsistent error UX | `RequestValidationError` handler shows the 404 page |
| 3 | `StaticFiles(directory="static")` and templates were relative to the working directory | App failed to start when launched from another folder | Paths resolved from `Path(__file__)` |
| 4 | Behind an HTTPS proxy, `url_for` produced `http://` links | Stylesheet blocked as mixed content on the deployed site | Start Uvicorn with `--proxy-headers --forwarded-allow-ips="*"` (deployment config) |
| 5 | `category` query parameter was put into the alert CSS class unchecked | Minor: arbitrary class names (Jinja2 autoescaping prevented script injection) | Only `success`/`danger` accepted |

## Additions for the Public Demo

- `DATABASE_PATH` env var; `DEMO_MODE=1` seeds four fictional sample records, shows a banner, enables `POST /demo/reset`.
- `render.yaml` and `.github/workflows/tests.yml`.

## Deployment Risks

- **SQLite on Render free tier is ephemeral.** There is no persistent disk on the free plan; the file is lost on restart, redeploy, or spin-down after ~15 minutes idle. Handled by re-seeding sample data and stating this in the banner and README.
- **Cold start** up to ~1 minute after inactivity.
- **Shared data**: no authentication, so all visitors see the same records.

## Security Review

| Area | Status |
| --- | --- |
| SQL injection | Protected: every query uses `?` placeholders; the dynamic `WHERE` only joins fixed strings. A test sends `' OR '1'='1` as search text |
| XSS | Jinja2 autoescaping is on for `.html` templates (Starlette default) |
| Stored `javascript:` links | Blocked: only http/https URLs pass validation (tested) |
| CSRF | Not protected (no auth, no tokens). Acceptable for a demo, required before adding accounts |
| Message spoofing | `?message=` text is user-controlled and shown in the alert (escaped). Low risk; could use server-side flash messages |
| Secrets | None used |

## Other Observations (not changed)

- `with sqlite3.connect(...) as connection:` commits or rolls back, but **does not close** the connection. CPython closes it when garbage-collected; explicit `contextlib.closing` would be cleaner.
- Sync `def` routes run in FastAPI's threadpool; that is the right choice for blocking `sqlite3` calls.
- No pagination, no sorting options, no authentication.

## Resume Claims vs Evidence

| Claim | Evidence | Verdict |
| --- | --- | --- |
| FastAPI app with add, view, edit, delete, search, status filter | Routes in `app.py`; tests `test_add/edit/delete_application`, `test_search_*`, `test_status_filter` | Supported |
| SQLite via `sqlite3` with parameterized queries | `get_db_connection()`, all `execute(..., params)` calls | Supported |
| Server-side validation for required fields, statuses, dates, URLs | `validate_application_form()` | Supported. Original tests covered required fields and status; date/URL tests were added on `interview-demo` |
| Responsive Jinja2 + Bootstrap 5 with messages, badges, empty states, custom 404/500 | Templates, `style.css` | Supported, but the **500 page did not render for raised 500 errors** in the original code (fixed) |
| Pytest + TestClient for page loading, CRUD, search, filtering, validation, invalid IDs | `tests/test_app.py` (10 tests) | Supported |
