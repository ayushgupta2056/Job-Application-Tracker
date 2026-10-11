"""Extra tests added on the interview-demo branch.

The original suite lives in test_app.py. These cover the validation, error-page
and demo-mode paths that test_app.py does not exercise.
"""
import sqlite3

import pytest
from fastapi.testclient import TestClient

import app as app_module
from tests.test_app import client, count_applications, create_application  # noqa: F401


VALID_FORM = {
    "company": "Acme Corp",
    "role": "Backend Developer",
    "status": "Applied",
    "application_date": "2026-07-31",
    "location": "Remote",
    "job_link": "https://example.com/job",
    "notes": "",
}


@pytest.mark.parametrize("bad_date", ["2026-02-30", "31-07-2026", "not-a-date"])
def test_validation_rejects_invalid_date(client, bad_date):
    response = client.post("/add", data={**VALID_FORM, "application_date": bad_date})

    assert response.status_code == 200
    assert b"Application date must be a valid date." in response.content
    assert count_applications() == 0


@pytest.mark.parametrize("bad_link", ["example.com/job", "ftp://example.com/job", "https://", "javascript:alert(1)"])
def test_validation_rejects_invalid_job_link(client, bad_link):
    response = client.post("/add", data={**VALID_FORM, "job_link": bad_link})

    assert response.status_code == 200
    assert b"Job link must be a valid URL" in response.content
    assert count_applications() == 0


def test_job_link_is_optional(client):
    response = client.post("/add", data={**VALID_FORM, "job_link": ""}, follow_redirects=True)

    assert b"Application added successfully." in response.content
    assert count_applications() == 1


def test_validation_keeps_entered_values(client):
    response = client.post("/add", data={**VALID_FORM, "role": "", "company": "Keep Me Ltd"})

    assert b"Job role is required." in response.content
    assert b'value="Keep Me Ltd"' in response.content


def test_edit_validation_does_not_change_record(client):
    application_id = create_application(company="Original Co")

    response = client.post(f"/edit/{application_id}", data={**VALID_FORM, "company": ""})

    assert b"Company name is required." in response.content
    with app_module.get_db_connection() as connection:
        company = connection.execute(
            "SELECT company FROM applications WHERE id = ?", (application_id,)
        ).fetchone()["company"]
    assert company == "Original Co"


def test_update_missing_id_returns_404(client):
    response = client.post("/edit/999999", data=VALID_FORM)

    assert response.status_code == 404
    assert b"Page not found" in response.content


def test_delete_missing_id_returns_404(client):
    response = client.post("/delete/999999")

    assert response.status_code == 404
    assert b"Page not found" in response.content


def test_non_numeric_id_shows_custom_404(client):
    response = client.get("/edit/abc")

    assert response.status_code == 404
    assert b"Page not found" in response.content


def test_unknown_page_shows_custom_404(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert b"Page not found" in response.content


def test_database_error_shows_custom_500(client, monkeypatch):
    def broken_connection():
        raise sqlite3.DatabaseError("simulated failure")

    monkeypatch.setattr(app_module, "get_db_connection", broken_connection)

    response = client.get("/")

    assert response.status_code == 500
    assert b"Something went wrong" in response.content


def test_search_and_status_filter_together(client):
    create_application(company="Acme Corp", role="Backend Developer", status="Applied")
    create_application(company="Acme Labs", role="Data Analyst", status="Interview")
    create_application(company="Bright Labs", role="Python Developer", status="Interview")

    response = client.get("/?search=Acme&status=Interview")

    assert b"Acme Labs" in response.content
    assert b"Acme Corp" not in response.content
    assert b"Bright Labs" not in response.content


def test_search_input_is_treated_as_text_not_sql(client):
    create_application(company="Acme Corp")

    response = client.get("/", params={"search": "' OR '1'='1"})

    assert response.status_code == 200
    assert b"Acme Corp" not in response.content
    assert b"No applications found" in response.content
    assert count_applications() == 1


def test_empty_state_is_shown(client):
    response = client.get("/")

    assert b"No applications found" in response.content


def test_newest_application_is_listed_first(client):
    create_application(company="Older Co")
    create_application(company="Newer Co")

    body = client.get("/").text

    assert body.index("Newer Co") < body.index("Older Co")


def test_demo_reset_is_disabled_outside_demo_mode(client):
    response = client.post("/demo/reset")

    assert response.status_code == 404


def test_demo_reset_restores_sample_records(client, monkeypatch):
    monkeypatch.setattr(app_module, "DEMO_MODE", True)
    create_application(company="Temporary Co")

    response = client.post("/demo/reset", follow_redirects=True)

    assert b"Demo data was reset" in response.content
    assert b"Temporary Co" not in response.content
    assert count_applications() == len(app_module.SAMPLE_APPLICATIONS)
