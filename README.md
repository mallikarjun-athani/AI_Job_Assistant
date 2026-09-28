# AI Job Application Assistant

## Overview
A full-stack AI-powered platform for analyzing resumes, matching candidates with jobs, generating job-specific resumes and cover letters, and tracking applications.

## Current Phase
Phase 2 - Authentication & User Profile

The foundation includes a custom email-based user model, registration, login, protected dashboard, profile editing, password changes, and logout. Resume, AI, job, and application features are not implemented in this phase.

## Tech Stack
- Python
- Django
- PostgreSQL
- HTML
- CSS
- JavaScript

## Project Structure
```text
ai-job-application-assistant/
|-- backend/
|   |-- manage.py
|   |-- config/
|   |-- accounts/
|   |-- resumes/
|   |-- jobs/
|   |-- applications/
|   |-- matching/
|   `-- ai_assistant/
|-- frontend/
|   `-- templates/
|-- media/
|-- static/
|-- .env
|-- .env.example
|-- .gitignore
|-- requirements.txt
`-- README.md
```

## Setup

Run commands from the project root (the directory containing `requirements.txt`).

1. Clone or download the project, then open its root directory in a terminal.
2. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

3. Activate it on Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. In Command Prompt, use `.venv\Scripts\activate.bat`.

4. Install the project dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

   Generate a development secret key and put its output in `.env`:

   ```powershell
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

5. Install PostgreSQL if it is not already installed, and create a database. For example, from `psql` as a PostgreSQL administrator:

   ```sql
   CREATE ROLE ai_job_assistant_user LOGIN;
   \password ai_job_assistant_user
   CREATE DATABASE ai_job_assistant OWNER ai_job_assistant_user;
   ```

   The `\password` command prompts for a password without putting it in SQL history. Keep that password private.

6. Copy `.env.example` to `.env` (PowerShell: `Copy-Item .env.example .env`) if `.env` does not already exist. Set `SECRET_KEY` to the generated key, `DATABASE_NAME` to `ai_job_assistant`, `DATABASE_USER` to `ai_job_assistant_user`, and `DATABASE_PASSWORD` to the role password. Keep `.env` out of version control. `DATABASE_HOST` and `DATABASE_PORT` default to `localhost` and `5432`.
7. Create and apply the initial custom-user migration before creating any accounts:

   ```powershell
   cd backend
   python manage.py makemigrations accounts
   python manage.py migrate
   ```

8. Start the development server:

   ```powershell
   python manage.py runserver
   ```

Open `http://127.0.0.1:8000/` for the home page. Register at `/register/`, then use the dashboard and profile links. Profile pictures accept JPEG, PNG, or WebP images up to 5 MB. `/health/` remains available for the health check. Run `python manage.py check` from `backend` before starting the server.

## Phase 2 URLs
- `/register/` creates an account and profile, then signs the user in.
- `/login/` and `/logout/` use Django authentication and sessions.
- `/dashboard/` requires authentication.
- `/profile/` edits the signed-in user's own profile.
- `/change-password/` uses Django's built-in password change form.

Run the automated test suite from `backend` with `python manage.py test`.

## Important Files
- `backend/manage.py` is the command-line entry point for Django tasks.
- `backend/config/settings.py` loads local environment settings, configures PostgreSQL, and selects `accounts.User` as the authentication model.
- `backend/accounts/models.py` defines the custom user and one-to-one profile.
- `backend/accounts/forms.py` validates registration, login, and profile updates.
- `backend/accounts/views.py` handles registration, the dashboard, profile updates, and password changes.
- `frontend/templates/base.html` provides shared navigation and messages; `static/css/site.css` styles the pages.
- `.env.example` lists required local settings. `.env` holds machine-specific values and is ignored by Git.
- `requirements.txt` lists only the packages needed for this foundation.