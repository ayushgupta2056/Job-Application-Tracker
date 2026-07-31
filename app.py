import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, abort, flash, redirect, render_template, request, url_for


app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key"
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
        abort(404)

    return application


@app.route("/")
def index():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

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
        abort(500)

    return render_template(
        "index.html",
        applications=applications,
        search=search,
        selected_status=status,
        statuses=STATUSES,
    )


@app.route("/add", methods=["GET", "POST"])
def add_job():
    form_data = {
        "company": "",
        "role": "",
        "status": "Applied",
        "application_date": "",
        "location": "",
        "job_link": "",
        "notes": "",
    }

    if request.method == "POST":
        form_data, errors = validate_application_form(request.form)

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("add_job.html", form_data=form_data, statuses=STATUSES)

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
            abort(500)

        flash("Application added successfully.", "success")
        return redirect(url_for("index"))

    return render_template("add_job.html", form_data=form_data, statuses=STATUSES)


@app.route("/edit/<int:application_id>", methods=["GET", "POST"])
def edit_job(application_id):
    application = get_application_or_404(application_id)
    form_data = dict(application)

    if request.method == "POST":
        form_data, errors = validate_application_form(request.form)

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "edit_job.html",
                application_id=application_id,
                form_data=form_data,
                statuses=STATUSES,
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
            abort(500)

        flash("Application updated successfully.", "success")
        return redirect(url_for("index"))

    return render_template(
        "edit_job.html",
        application_id=application_id,
        form_data=form_data,
        statuses=STATUSES,
    )


@app.route("/delete/<int:application_id>", methods=["POST"])
def delete_job(application_id):
    application = get_application_or_404(application_id)

    try:
        with get_db_connection() as connection:
            connection.execute(
                "DELETE FROM applications WHERE id = ?",
                (application_id,),
            )
    except sqlite3.DatabaseError:
        abort(500)

    flash(f"Application for {application['company']} deleted successfully.", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html"), 500


init_db()


if __name__ == "__main__":
    app.run(debug=True)
