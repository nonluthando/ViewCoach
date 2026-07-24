# Adaptive Interview Preparation Coach

A Django application for creating structured interview material, following role-based learning paths and receiving a focused daily study plan based on what matters now.

The repository currently contains **Milestones 0 through 3.2**.

## Implemented

### Milestone 0 — Production foundation

- Django 5.2 foundation;
- PostgreSQL in local, test and production environments;
- custom email-based user model;
- registration, login, logout and protected dashboard;
- database-aware health endpoint;
- pytest, Ruff and GitHub Actions CI;
- Render blueprint draft.

### Milestone 1 — Structured question library

- polymorphic base `Question` model;
- technical, behavioural and repository-debugging question types;
- type-specific create, edit and detail experiences;
- private user-owned libraries;
- search and filters for type, status and difficulty;
- progressive reveal for technical questions;
- debugging diagnosis reveal;
- admin support, migration and authorization tests;
- dashboard question summary.

### Milestone 1.1 — Bulk question import

- pasted text, TXT, Markdown, CSV, DOCX and text-based PDF imports;
- resumable review batches with editable generated titles;
- per-item type overrides and duplicate detection;
- transactional, idempotent question creation;
- temporary source deletion after successful import;
- imported questions marked **Needs notes**;
- individual and bulk **Mark ready** validation.

### Milestone 2 — Review engine

- deterministic Again, Hard, Good and Easy scheduling;
- due and upcoming review queues;
- review history and dashboard summaries;
- ownership validation around every review state.

### Milestones 3 and 3.1 — Learning roadmaps

- 12 built-in role, skill and practice roadmaps with 419 topics;
- per-user roadmap and topic progress;
- topic workspaces with private notes and saved learning resources.

### Milestone 3.2 — Adaptive study planner

- a persisted daily plan generated from available study time;
- deterministic priority for due reviews, active roadmap work, recent weak areas and fresh practice;
- transparent rationales and time estimates for every recommendation;
- task completion, plan regeneration and study-session tracking;
- dashboard integration that gives users a clear next action.

## Architecture decisions

- Modular Django monolith.
- PostgreSQL from the beginning; no application SQLite fallback.
- Custom user model before the first migration.
- Server-rendered Django interface first.
- Concrete base question plus typed child models.
- Deterministic study logic remains separate from future AI behaviour.

See [`docs/architecture/overview.md`](docs/architecture/overview.md), [`docs/architecture/adaptive-study-planner.md`](docs/architecture/adaptive-study-planner.md) and [`docs/adr/`](docs/adr/).

## Local setup

### 1. Create a Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Create the local environment file

```bash
cp .env.example .env
```

The project deliberately does not automatically load `.env`. Export the variables in your shell or configure them in your IDE. The defaults in `config.settings.local` are sufficient when using the included local PostgreSQL credentials.

### 3. Start PostgreSQL

```bash
docker compose up -d postgres
```

### 4. Apply migrations

```bash
python3 manage.py migrate
```

### 5. Start Django

```bash
python3 manage.py runserver
```

Open `http://127.0.0.1:8000/` and visit `/questions/` after signing in.

## Tests

The committed test settings use PostgreSQL. Django creates and removes a separate test database on the configured PostgreSQL server.

```bash
python3 -m pytest
ruff check .
python3 manage.py makemigrations --check --dry-run
```

## Create an administrator

```bash
python3 manage.py createsuperuser
```

The login identifier is the email address.

## Production settings

Production requires:

- `DJANGO_SETTINGS_MODULE=config.settings.production`;
- `DJANGO_SECRET_KEY`;
- `DATABASE_URL`;
- either `RENDER_EXTERNAL_HOSTNAME` or `DJANGO_ALLOWED_HOSTS`.

The included `render.yaml` is a deployment draft. Review the current Render plan and database settings before creating a Blueprint.

## First-migration warning

`accounts.User` is referenced by `AUTH_USER_MODEL` and is created in `accounts/0001_initial.py`. Do not run Django's default migrations before this model exists. Replacing the user model after dependent migrations have been applied is intentionally avoided.

## Built-in question library

ViewCoach ships with a curated starter library. After applying migrations locally, seed or refresh it with:

```bash
python manage.py seed_question_bank
```

The command is idempotent and is also run by `build.sh` during Render deployments. The curated core bank contains 100 questions: 30 technical, 50 concept, 10 debugging and 10 behavioural. Built-in questions are shared and read-only; each user stores private bookmarks, progress and notes separately.

## Built-in learning roadmaps

ViewCoach also ships with fixed role, skill and practice roadmaps. Seed or refresh them with:

```bash
python manage.py seed_roadmaps
```

The command is idempotent and is run by `build.sh` during Render deployments. The first catalogue contains 12 roadmaps and 419 topics across AI engineering, backend, full-stack, data analysis, prompt engineering, AI agents, Python, Java, Python for data analysis, system design, data structures and algorithms, and LeetCode interview practice.
