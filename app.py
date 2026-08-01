import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DATABASE = Path(__file__).with_name("jobs.db")
STATUSES = ["Applied", "Interview", "Rejected", "Selected"]


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


@app.exception_handler(404)
def page_not_found(request: Request, exc):
    return templates.TemplateResponse(
        request,
        "404.html",
        {"messages": []},
        status_code=404,
    )


@app.exception_handler(500)
def internal_server_error(request: Request, exc):
    return templates.TemplateResponse(
        request,
        "500.html",
        {"messages": []},
        status_code=500,
    )


init_db()


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)
