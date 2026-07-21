# Adaptive Interview Preparation Coach

A Django application for creating structured interview material, practising it progressively and later receiving a focused study plan based on what matters now.

The repository currently contains **Milestones 0 and 1**.

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

Spaced repetition, reviews, the Focus Engine, goals and AI are intentionally not part of this milestone.

## Architecture decisions

- Modular Django monolith.
- PostgreSQL from the beginning; no application SQLite fallback.
- Custom user model before the first migration.
- Server-rendered Django interface first.
- Concrete base question plus typed child models.
- Deterministic study logic remains separate from future AI behaviour.

See [`docs/architecture/overview.md`](docs/architecture/overview.md) and [`docs/adr/`](docs/adr/).

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
