import pytest

import app as app_module


@pytest.fixture
def client(tmp_path):
    app_module.DATABASE = tmp_path / "test_jobs.db"
    app_module.app.config["TESTING"] = True
    app_module.init_db()

    with app_module.app.test_client() as test_client:
        yield test_client


def count_applications():
    with app_module.get_db_connection() as connection:
        return connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0]


def create_application(
    company="Acme Corp",
    role="Backend Developer",
    status="Applied",
    application_date="2026-07-31",
):
    with app_module.get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO applications (company, role, status, application_date, location, job_link, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company,
                role,
                status,
                application_date,
                "Remote",
                "https://example.com/job",
                "Test notes",
            ),
        )
        return cursor.lastrowid


def test_homepage_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Job Applications" in response.data


def test_add_application(client):
    response = client.post(
        "/add",
        data={
            "company": "Acme Corp",
            "role": "Backend Developer",
            "status": "Applied",
            "application_date": "2026-07-31",
            "location": "Remote",
            "job_link": "https://example.com/job",
            "notes": "Follow up next week",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Application added successfully." in response.data
    assert count_applications() == 1


def test_edit_application(client):
    application_id = create_application()

    response = client.post(
        f"/edit/{application_id}",
        data={
            "company": "Acme Updated",
            "role": "Python Developer",
            "status": "Interview",
            "application_date": "2026-08-01",
            "location": "Bengaluru",
            "job_link": "https://example.com/updated",
            "notes": "Interview scheduled",
        },
        follow_redirects=True,
    )

    with app_module.get_db_connection() as connection:
        application = connection.execute(
            "SELECT company, role, status FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()

    assert response.status_code == 200
    assert b"Application updated successfully." in response.data
    assert application["company"] == "Acme Updated"
    assert application["role"] == "Python Developer"
    assert application["status"] == "Interview"


def test_delete_application(client):
    application_id = create_application()

    response = client.post(f"/delete/{application_id}", follow_redirects=True)

    assert response.status_code == 200
    assert b"deleted successfully" in response.data
    assert count_applications() == 0


def test_search_company(client):
    create_application(company="Acme Corp", role="Backend Developer")
    create_application(company="Bright Labs", role="Python Developer")

    response = client.get("/?search=Acme")

    assert response.status_code == 200
    assert b"Acme Corp" in response.data
    assert b"Bright Labs" not in response.data


def test_search_role(client):
    create_application(company="Acme Corp", role="Backend Developer")
    create_application(company="Bright Labs", role="Python Developer")

    response = client.get("/?search=Python")

    assert response.status_code == 200
    assert b"Python Developer" in response.data
    assert b"Acme Corp" not in response.data


def test_status_filter(client):
    create_application(company="Acme Corp", status="Applied")
    create_application(company="Bright Labs", status="Interview")

    response = client.get("/?status=Interview")

    assert response.status_code == 200
    assert b"Bright Labs" in response.data
    assert b"Acme Corp" not in response.data


def test_invalid_id_returns_404(client):
    response = client.get("/edit/999999")

    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_validation_rejects_missing_required_fields(client):
    response = client.post(
        "/add",
        data={
            "company": "",
            "role": "",
            "status": "Applied",
            "application_date": "",
        },
    )

    assert response.status_code == 200
    assert b"Company name is required." in response.data
    assert b"Job role is required." in response.data
    assert b"Application date is required." in response.data
    assert count_applications() == 0


def test_validation_rejects_invalid_status(client):
    response = client.post(
        "/add",
        data={
            "company": "Acme Corp",
            "role": "Backend Developer",
            "status": "Unknown",
            "application_date": "2026-07-31",
        },
    )

    assert response.status_code == 200
    assert b"Please select a valid status." in response.data
    assert count_applications() == 0
