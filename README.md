# AI Job Application Assistant

## Overview
A full-stack AI-powered platform for analyzing resumes, matching candidates with jobs, generating job-specific resumes and cover letters, and tracking applications.

## Current Phase
Phase 5 - Real Job Discovery

The foundation includes a custom email-based user model, registration, login, protected dashboard, profile editing, password changes, and logout. Phase 3 adds private PDF/DOCX resume uploads and text extraction. Phase 4 adds owner-protected, Groq-powered structured resume analysis. Job matching, resume generation, cover letters, and application tracking are not implemented in this phase.

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
|   |   `-- templates/resumes/resume_analysis.html
|   |-- jobs/
|   |-- applications/
|   |-- matching/
|   `-- ai_assistant/
|       |-- prompts.py
|       |-- services.py
|       `-- validators.py
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

6. Copy `.env.example` to `.env` (PowerShell: `Copy-Item .env.example .env`) if `.env` does not already exist. Set `SECRET_KEY` to the generated key, `DATABASE_NAME` to `ai_job_assistant`, `DATABASE_USER` to `ai_job_assistant_user`, and `DATABASE_PASSWORD` to the role password. Set `GROQ_API_KEY` to your private Groq API key and `GROQ_MODEL` to the model identifier (defaults to `openai/gpt-oss-20b`). Keep `.env` out of version control. `DATABASE_HOST` and `DATABASE_PORT` default to `localhost` and `5432`.
7. Create and apply the initial custom-user migration before creating any accounts:

   ```powershell
   cd backend
   python manage.py makemigrations accounts resumes
   python manage.py migrate
   ```

8. Start the development server:

   ```powershell
   python manage.py runserver
   ```

Open `http://127.0.0.1:8000/` for the home page. Register at `/register/`, then use the dashboard and profile links. Profile pictures accept JPEG, PNG, or WebP images up to 5 MB. `/health/` remains available for the health check. Run `python manage.py check` from `backend` before starting the server.

## Phase 3 — Resume Upload & Text Extraction
- Authenticated users can upload PDF and DOCX resumes up to 5 MB.
- File extensions and document contents are validated before storage.
- PDF and DOCX text is extracted locally and stored with each resume record.
- Users can view extracted text, download their original file, and delete their own resumes.
- Resume files are stored under `media/resumes/user_<id>/` and downloads are served through an authenticated, owner-checked view. Do not configure a public media server route for resumes in production.
- The dashboard and authenticated navigation link to resume management.

New dependencies: `PyMuPDF` for PDF parsing and `python-docx` for DOCX parsing. Install them with `python -m pip install -r requirements.txt`.

After updating dependencies, create and apply the resume migration from `backend`:

```powershell
python manage.py makemigrations resumes
python manage.py migrate
```

Visit `/resumes/` while signed in to upload and manage resumes. `/resumes/<id>/` shows metadata and extracted text; use its Download and Delete actions to manage the original file and record.

## Phase 4 — Groq AI Resume Analyzer
- Calls the official Groq Python SDK from `backend/ai_assistant/services.py`; Django views do not call the SDK directly.
- Uses `GROQ_MODEL` from settings, defaulting to `openai/gpt-oss-20b`, with Groq JSON Schema structured output. The response is parsed and validated before any analysis is stored.
- Stores personal information, summary, skills, education, experience, projects, certifications, languages, and keywords as a single `ResumeAnalysis` one-to-one record with PostgreSQL JSON fields for structured values.
- Re-analysis updates the existing record instead of creating a duplicate. A normalized input over 50,000 characters is rejected rather than truncated.
- Only the authenticated resume owner can analyze or view its analysis. Analysis is submitted by CSRF-protected POST; resume content, API keys, and full AI responses are not logged.
- The resume list shows analysis status and Analyze, Re-analyze, and View Analysis actions. The dashboard shows total and analyzed resume counts.

Configure these values in the project-root `.env` file; `.env.example` contains empty/example values only:

```dotenv
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
```

Install the official Groq client with `python -m pip install -r requirements.txt`. From `backend`, apply the analysis migration and run tests:

```powershell
python manage.py makemigrations resumes
python manage.py migrate
python manage.py test
```

The test suite mocks the analyzer/Groq SDK and makes no real API requests. New routes are `/resumes/<id>/analyze/` (POST only) and `/resumes/<id>/analysis/` (owner-only page).

## Phase 5 — Real Job Discovery
- Adzuna is the initial job data provider and is isolated behind a dedicated provider layer in `backend/jobs/providers/`.
- `.env` and `.env.example` include `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `ADZUNA_COUNTRY`, and `ADZUNA_BASE_URL`; values remain server-side and are never exposed to the browser.
- Discovery starts from the latest analyzed resume and the user profile location; it builds up to five de-duplicated job search queries from `ResumeAnalysis.target_roles` plus fallback skills/keywords.
- Search results are normalized into a shared internal `Job` model, stored in PostgreSQL, and deduplicated by `provider + external_id` before a new record is created.
- The project stores only the normalized fields it needs for display and future matching, while `raw_data` keeps the provider payload as a structured JSON record for debugging.
- Users click a dashboard action to trigger a discovery request; the request does not run on page refresh or dashboard load and does not call the AI API for job matching.
- Phase 5 discovers and stores real jobs. Job matching and match scores are implemented in Phase 6.

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
- `requirements.txt` lists the packages used by the current project phase.