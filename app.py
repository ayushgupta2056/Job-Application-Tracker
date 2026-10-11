import os
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

DATABASE = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "jobs.db"))
STATUSES = ["Applied", "Interview", "Rejected", "Selected"]
MESSAGE_CATEGORIES = ["success", "danger"]

# Demo mode is only enabled on the public deployment (see render.yaml).
DEMO_MODE = os.environ.get("DEMO_MODE") == "1"
templates.env.globals["demo_mode"] = DEMO_MODE

SAMPLE_APPLICATIONS = [
    ("Acme Corp", "Backend Developer", "Applied", "2026-09-28", "Remote", "https://example.com/jobs/backend", "Sample record"),
    ("Bright Labs", "Python Developer", "Interview", "2026-09-30", "Bengaluru", "https://example.com/jobs/python", "Sample record"),
    ("Cloud Nine", "QA Automation Engineer", "Rejected", "2026-09-15", "Pune", "", "Sample record"),
    ("DataWorks", "Software Engineer", "Selected", "2026-09-10", "Hyderabad", "https://example.com/jobs/swe", "Sample record"),
]


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                application_date TEXT NOT NULL,
                location TEXT,
                job_link TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def seed_demo_data():
    with get_db_connection() as connection:
        if connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0]:
            return
        connection.executemany(
            """
            INSERT INTO applications (company, role, status, application_date, location, job_link, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            SAMPLE_APPLICATIONS,
        )


def default_form_data():
    return {
        "company": "",
        "role": "",
        "status": "Applied",
        "application_date": "",
        "location": "",
        "job_link": "",
        "notes": "",
    }


def validate_application_form(form):
    data = {
        "company": form.get("company", "").strip(),
        "role": form.get("role", "").strip(),
        "status": form.get("status", "").strip(),
        "application_date": form.get("application_date", "").strip(),
        "location": form.get("location", "").strip(),
        "job_link": form.get("job_link", "").strip(),
        "notes": form.get("notes", "").strip(),
    }
    errors = []

    if not data["company"]:
        errors.append("Company name is required.")

    if not data["role"]:
        errors.append("Job role is required.")

    if data["status"] not in STATUSES:
        errors.append("Please select a valid status.")

    if not data["application_date"]:
        errors.append("Application date is required.")
    else:
        try:
            datetime.strptime(data["application_date"], "%Y-%m-%d")
        except ValueError:
            errors.append("Application date must be a valid date.")

    if data["job_link"]:
        parsed_url = urlparse(data["job_link"])
        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            errors.append("Job link must be a valid URL starting with http:// or https://.")

    return data, errors


def get_application_or_404(application_id):
    with get_db_connection() as connection:
        application = connection.execute(
            "SELECT * FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()

    if application is None:
        raise HTTPException(status_code=404)

    return application


def redirect_with_message(url, message, category="success"):
    return RedirectResponse(
        url=f"{url}?message={quote(message)}&category={category}",
        status_code=303,
    )


@app.get("/", name="index")
def index(request: Request, search: str = "", status: str = "", message: str = "", category: str = "success"):
    search = search.strip()
    status = status.strip()

    query = "SELECT * FROM applications"
    conditions = []
    parameters = []

    if search:
        conditions.append("(company LIKE ? OR role LIKE ?)")
        search_value = f"%{search}%"
        parameters.extend([search_value, search_value])

    if status in STATUSES:
        conditions.append("status = ?")
        parameters.append(status)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC, id DESC"

    try:
        with get_db_connection() as connection:
            applications = connection.execute(query, parameters).fetchall()
    except sqlite3.DatabaseError:
        raise HTTPException(status_code=500)

    if category not in MESSAGE_CATEGORIES:
        category = "success"
    messages = [(category, message)] if message else []

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "applications": applications,
            "search": search,
            "selected_status": status,
            "statuses": STATUSES,
            "messages": messages,
        },
    )


@app.get("/add", name="add_job")
def add_job_form(request: Request):
    return templates.TemplateResponse(
        request,
        "add_job.html",
        {
            "form_data": default_form_data(),
            "statuses": STATUSES,
            "messages": [],
        },
    )


@app.post("/add", name="create_job")
async def create_job(request: Request):
    form_data, errors = validate_application_form(await request.form())

    if errors:
        return templates.TemplateResponse(
            request,
            "add_job.html",
            {
                "form_data": form_data,
                "statuses": STATUSES,
                "messages": [("danger", error) for error in errors],
            },
        )

    try:
        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO applications (
                    company, role, status, application_date, location, job_link, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    form_data["company"],
                    form_data["role"],
                    form_data["status"],
                    form_data["application_date"],
                    form_data["location"],
                    form_data["job_link"],
                    form_data["notes"],
                ),
            )
    except sqlite3.DatabaseError:
        raise HTTPException(status_code=500)

    return redirect_with_message("/", "Application added successfully.")


@app.get("/edit/{application_id}", name="edit_job")
def edit_job_form(request: Request, application_id: int):
    application = get_application_or_404(application_id)

    return templates.TemplateResponse(
        request,
        "edit_job.html",
        {
            "application_id": application_id,
            "form_data": dict(application),
            "statuses": STATUSES,
            "messages": [],
        },
    )


@app.post("/edit/{application_id}", name="update_job")
async def update_job(request: Request, application_id: int):
    get_application_or_404(application_id)
    form_data, errors = validate_application_form(await request.form())

    if errors:
        return templates.TemplateResponse(
            request,
            "edit_job.html",
            {
                "application_id": application_id,
                "form_data": form_data,
                "statuses": STATUSES,
                "messages": [("danger", error) for error in errors],
            },
        )

    try:
        with get_db_connection() as connection:
            connection.execute(
                """
                UPDATE applications
                SET company = ?,
                    role = ?,
                    status = ?,
                    application_date = ?,
                    location = ?,
                    job_link = ?,
                    notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    form_data["company"],
                    form_data["role"],
                    form_data["status"],
                    form_data["application_date"],
                    form_data["location"],
                    form_data["job_link"],
                    form_data["notes"],
                    application_id,
                ),
            )
    except sqlite3.DatabaseError:
        raise HTTPException(status_code=500)

    return redirect_with_message("/", "Application updated successfully.")


@app.post("/delete/{application_id}", name="delete_job")
def delete_job(application_id: int):
    application = get_application_or_404(application_id)

    try:
        with get_db_connection() as connection:
            connection.execute(
                "DELETE FROM applications WHERE id = ?",
                (application_id,),
            )
    except sqlite3.DatabaseError:
        raise HTTPException(status_code=500)

    return redirect_with_message(
        "/",
        f"Application for {application['company']} deleted successfully.",
    )


@app.post("/demo/reset", name="reset_demo")
def reset_demo():
    if not DEMO_MODE:
        raise HTTPException(status_code=404)

    with get_db_connection() as connection:
        connection.execute("DELETE FROM applications")
    seed_demo_data()

    return redirect_with_message("/", "Demo data was reset to the sample records.")


def page_not_found(request: Request):
    return templates.TemplateResponse(
        request,
        "404.html",
        {"messages": []},
        status_code=404,
    )


def internal_server_error(request: Request):
    return templates.TemplateResponse(
        request,
        "500.html",
        {"messages": []},
        status_code=500,
    )


# Raised HTTPExceptions (404 and 500) go through this handler. A handler
# registered only for 500 is used for unhandled errors, not for HTTPException(500).
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc):
    if exc.status_code == 404:
        return page_not_found(request)
    if exc.status_code == 500:
        return internal_server_error(request)
    return await default_http_exception_handler(request, exc)


# A non-numeric record ID such as /edit/abc is treated as a missing record.
@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc):
    return page_not_found(request)


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc):
    return internal_server_error(request)


init_db()
if DEMO_MODE:
    seed_demo_data()


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)
