# Architecture overview

## Current milestone

Milestone 0 creates only the application shell and authentication foundation. It does not introduce interview goals, question-bank entities, planning rules or AI integrations.

## System shape

The project is a modular Django monolith:

```text
Browser
   |
Django views and forms
   |
Application services       (introduced with domain milestones)
   |
Deterministic domain rules (introduced with planning)
   |
Django ORM
   |
PostgreSQL
```

RAG and external AI-provider integration will later be added as bounded subsystems inside the monolith, not as premature microservices.

## Current modules

### `apps.accounts`

Owns identity and authentication-specific behaviour:

- custom `User` model;
- email-based login identity;
- account creation forms;
- user administration;
- signup route.

It must not accumulate interview preferences, goals, practice history or AI memory. Those belong to later domain modules.

### `apps.core`

Owns application-level pages and technical endpoints that do not belong to a product domain:

- public landing page;
- protected dashboard shell;
- database-aware health endpoint.

It must not become a general dumping ground. Shared product logic should live in the domain that owns it.

### `config`

Owns deployment and framework configuration:

- URL composition;
- WSGI and ASGI entry points;
- local, test and production settings.

## Settings strategy

- `base.py`: settings shared by every environment.
- `local.py`: local PostgreSQL and development behaviour.
- `test.py`: PostgreSQL tests, deterministic password hashing and in-memory email.
- `production.py`: required secrets, HTTPS controls, WhiteNoise and managed PostgreSQL.

SQLite is deliberately not used, because PostgreSQL-specific behaviour will later include pgvector and database constraints that should be exercised during development and CI.

## Authentication decision

The application uses a custom `User` model from the first migration. Email is the unique login identity and the inherited username field is removed.

Future user-specific profile data should normally use one-to-one or foreign-key models rather than expanding the authentication table indiscriminately.

## Future module direction

Later milestones may add:

- `goals`;
- `question_bank`;
- `practice`;
- `planning`;
- `knowledge`;
- `ai`;
- `mock_interviews`;
- `evaluation`.

Each module should own its models, services, selectors, rules and tests. Views should coordinate requests, not calculate mastery or call AI providers directly.
