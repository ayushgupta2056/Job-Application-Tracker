# Test Report — Job Application Tracker

All results below come from real executions on 2026-10-11.

## Summary

| Run | Where | Result |
| --- | --- | --- |
| Original suite, unmodified `main` (`b669547`) | Windows 11, Python 3.12.10 | **10 passed**, 0 failed |
| Full suite, `interview-demo` | Windows 11, Python 3.12.10, 12:51 UTC | **31 passed**, 0 failed, 0 skipped |
| Full suite, `interview-demo` (`914050f`) | GitHub Actions, ubuntu-latest, Python 3.12 ([run](https://github.com/ayushgupta2056/Job-Application-Tracker/actions/runs/38139467265)) | **31 passed**, 0 failed |
| New tests against the *original* `app.py` | Windows 11 | 18 passed, **3 failed** (custom 500 page, non-numeric ID, demo reset) — confirms the tests detect the fixed defects |
| Manual smoke test of the live demo | https://job-application-tracker-demo-xmoh.onrender.com via curl | All checks below passed |

Test isolation: the `client` fixture points `app.DATABASE` at a `tmp_path` file and calls
`init_db()`, so every test starts with an empty database and the real `jobs.db` is never touched.

## Automated Tests

### Original suite — `tests/test_app.py`

| Test | Expected | Actual | Status |
| --- | --- | --- | --- |
| test_homepage_loads | `GET /` → 200 with "Job Applications" | 200, heading present | PASS |
| test_add_application | Valid POST → redirect, success message, 1 row | As expected | PASS |
| test_edit_application | POST edit → row has new company/role/status | As expected | PASS |
| test_delete_application | POST delete → message, 0 rows | As expected | PASS |
| test_search_company | `?search=Acme` shows Acme only | As expected | PASS |
| test_search_role | `?search=Python` matches role only | As expected | PASS |
| test_status_filter | `?status=Interview` shows only Interview rows | As expected | PASS |
| test_invalid_id_returns_404 | `GET /edit/999999` → 404 page | 404, "Page not found" | PASS |
| test_validation_rejects_missing_required_fields | 3 required-field errors, no insert | As expected | PASS |
| test_validation_rejects_invalid_status | "Please select a valid status.", no insert | As expected | PASS |

### Added on `interview-demo` — `tests/test_additional_coverage.py`

| Test | Expected | Actual | Status |
| --- | --- | --- | --- |
| test_validation_rejects_invalid_date × 3 (`2026-02-30`, `31-07-2026`, `not-a-date`) | Date error, no insert | As expected | PASS |
| test_validation_rejects_invalid_job_link × 4 (`example.com/job`, `ftp://…`, `https://`, `javascript:alert(1)`) | URL error, no insert | As expected | PASS |
| test_job_link_is_optional | Empty link is accepted | Saved | PASS |
| test_validation_keeps_entered_values | Form redisplays typed company | `value="Keep Me Ltd"` present | PASS |
| test_edit_validation_does_not_change_record | Invalid edit leaves DB unchanged | Unchanged | PASS |
| test_update_missing_id_returns_404 | POST `/edit/999999` → 404 page | As expected | PASS |
| test_delete_missing_id_returns_404 | POST `/delete/999999` → 404 page | As expected | PASS |
| test_non_numeric_id_shows_custom_404 | `/edit/abc` → 404 page (was 422 JSON) | As expected | PASS |
| test_unknown_page_shows_custom_404 | Unknown URL → 404 page | As expected | PASS |
| test_database_error_shows_custom_500 | `sqlite3.DatabaseError` → 500 page (was JSON) | As expected | PASS |
| test_search_and_status_filter_together | Search + status combine with AND | Only "Acme Labs" | PASS |
| test_search_input_is_treated_as_text_not_sql | `' OR '1'='1` returns no rows, table intact | As expected | PASS |
| test_empty_state_is_shown | "No applications found" | As expected | PASS |
| test_newest_application_is_listed_first | Newer record above older | As expected | PASS |
| test_demo_reset_is_disabled_outside_demo_mode | `POST /demo/reset` → 404 | As expected | PASS |
| test_demo_reset_restores_sample_records | Reset → 4 sample rows | As expected | PASS |

**Totals:** 31 executed, 31 passed, 0 failed, 0 skipped.

## Live Deployment Checks (Render, 2026-10-11)

| Check | Expected | Actual | Status |
| --- | --- | --- | --- |
| Home page | 4 sample records, demo banner, https stylesheet | As expected | PASS |
| Add "Render Check Co" (Interview) | 303 redirect | 303 | PASS |
| Search "Render Check" | 1 match | 1 | PASS |
| Filter Interview | Bright Labs + Render Check Co | As expected | PASS |
| Edit status to Selected | 303, badge `status-selected` | As expected | PASS |
| Invalid date `2026-13-45` | Date error | Shown | PASS |
| Invalid link `foo` | URL error | Shown | PASS |
| Empty required fields | 3 errors | 3 | PASS |
| `/edit/99999`, `/edit/abc` | Custom 404 | 404 page both | PASS |
| Delete record | 303, record gone | As expected | PASS |
| Reset demo data | 4 sample rows | 4 | PASS |

## Remaining Issues

None failing. Known limitations (ephemeral SQLite on the free plan, no auth, no pagination)
are documented in the README.
