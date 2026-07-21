# Adaptive Interview Preparation Coach

A Django application that will combine structured interview practice, deterministic study planning and grounded retrieval-augmented explanations.

This repository currently contains **Milestone 0 only**:

- Django 5.2 foundation;
- PostgreSQL in local, test and production environments;
- custom email-based user model;
- registration, login, logout and protected dashboard;
- database-aware health endpoint;
- pytest baseline;
- GitHub Actions CI;
- Render blueprint draft.

No interview-goal, question-bank, planning or AI domain code belongs in this milestone.

## Architecture decisions

- Modular Django monolith.
- PostgreSQL from the beginning; no SQLite fallback.
- Custom user model before the first migration.
- Server-rendered Django interface first.
- Deterministic domain logic will remain separate from AI behaviour.

See [`docs/architecture/overview.md`](docs/architecture/overview.md) and [`docs/adr/`](docs/adr/).

## Local setup

### 1. Create a Python environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
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
python manage.py migrate
```

### 5. Start Django

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Tests

The tests also use PostgreSQL. Django creates and removes a separate test database on the configured PostgreSQL server.

```bash
pytest
ruff check .
python manage.py makemigrations --check --dry-run
```

## Create an administrator

```bash
python manage.py createsuperuser
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
