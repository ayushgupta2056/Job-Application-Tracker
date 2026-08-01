# Job Application Tracker

A FastAPI web app to keep track of job applications in one place.

I built this project to practice the main parts of a small backend web application: handling form submissions, storing data in SQLite, rendering pages with Jinja2, and testing the important flows with pytest.

## Features

- Add job applications
- View all saved applications
- Edit application details
- Delete applications with confirmation
- Search by company or job role
- Filter by status
- Use search and status filter together
- Show newest applications first
- Validate form input on the server
- Show success and error messages
- Handle missing pages and invalid records with custom error pages

## Tech Stack

| Area | Technology |
| --- | --- |
| Backend | Python, FastAPI, Uvicorn |
| Database | SQLite |
| Templates | Jinja2 |
| Frontend | HTML, CSS, Bootstrap 5 |
| Testing | pytest, FastAPI TestClient |

## Application Statuses

The app supports four application statuses:

- Applied
- Interview
- Rejected
- Selected

## Screenshots

### Homepage

![Homepage](screenshots/homepage.png)

### Add Application

![Add Application](screenshots/add-application.png)

### Edit Application

![Edit Application](screenshots/edit-application.png)

## Project Structure

```text
job-application-tracker/
|-- app.py
|-- jobs.db                 # created locally when the app runs
|-- requirements.txt
|-- README.md
|-- .gitignore
|
|-- templates/
|   |-- base.html
|   |-- index.html
|   |-- add_job.html
|   |-- edit_job.html
|   |-- 404.html
|   `-- 500.html
|
|-- static/
|   `-- style.css
|
|-- screenshots/
|   |-- homepage.png
|   |-- add-application.png
|   `-- edit-application.png
|
`-- tests/
    `-- test_app.py
```

## Database

The project uses SQLite through Python's built-in `sqlite3` module.

The database has one table: `applications`.

| Column | Description |
| --- | --- |
| id | Unique ID for each application |
| company | Company name |
| role | Job role |
| status | Current application status |
| application_date | Date of application |
| location | Job location |
| job_link | Link to the job posting |
| notes | Extra notes |
| created_at | When the record was created |
| updated_at | When the record was last updated |

The database file is created automatically when the app runs.

SQL queries use placeholders like `?` so user input is passed safely instead of being added directly into query strings.

## Routes

| Route | Method | Description |
| --- | --- | --- |
| `/` | GET | Shows the application list with search and filter options |
| `/add` | GET | Shows the add application form |
| `/add` | POST | Saves a new application |
| `/edit/{application_id}` | GET | Shows the edit form for an existing application |
| `/edit/{application_id}` | POST | Updates an existing application |
| `/delete/{application_id}` | POST | Deletes an application |

## Validation

The app validates form data in FastAPI before saving it to the database.

It checks that:

- Company name is not empty
- Job role is not empty
- Status is one of the allowed values
- Application date is provided and valid
- Job link is a valid `http://` or `https://` URL if entered

If validation fails, the app shows an error message and keeps the user's entered form values.

## Setup

Open PowerShell in the project folder.

Install the required packages:

```powershell
pip install -r requirements.txt
```

Run the app:

```powershell
python app.py
```

Open this URL in the browser:

```text
http://127.0.0.1:5000
```

## Running Tests

Run all tests:

```powershell
python -m pytest
```

Run tests with detailed output:

```powershell
python -m pytest -v
```

The tests use a temporary SQLite database, so they do not change the real `jobs.db` file.

The tests cover:

- Homepage loading
- Adding an application
- Editing an application
- Deleting an application
- Searching by company
- Searching by role
- Filtering by status
- Invalid ID handling
- Required field validation
- Invalid status validation

## Future Improvements

- Add pagination
- Add sorting options
- Add CSV export
- Add an archive option for old applications

## Resume Summary

Built a FastAPI and SQLite job application tracker with CRUD operations, search, filtering, server-side validation, custom error pages, Jinja2 templates, and pytest tests for the main application flows.
