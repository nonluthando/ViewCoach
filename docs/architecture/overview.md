# Architecture overview

## Current milestone

Milestone 1 establishes the structured question library: the product's first interview-preparation domain. Review scheduling, mastery, goals, daily planning and AI remain outside this boundary.

## System shape

The project is a modular Django monolith:

```text
Browser
   |
Django views and forms
   |
Domain modules
   |
Application services       (introduced when workflows cross model boundaries)
   |
Django ORM
   |
PostgreSQL
```

RAG and external AI-provider integration may later be added as bounded subsystems inside the monolith, not as premature microservices.

## Current modules

### `apps.accounts`

Owns identity and authentication-specific behaviour:

- custom `User` model;
- email-based login identity;
- account creation forms;
- user administration;
- signup route.

It must not accumulate question content, review history or AI memory.

### `apps.questions`

Owns user-created interview preparation material:

- concrete base `Question` records;
- `TechnicalQuestion`, `BehaviouralQuestion` and `DebugQuestion` child records;
- type-specific forms and detail experiences;
- library search and filtering;
- question ownership and authorization;
- progressive answer reveal.

The base table stores fields shared by every question. Typed child tables store only fields meaningful to that interview format. New formats can be introduced as new child models without adding unrelated nullable columns to every existing question.

The module does not own spaced repetition or mastery. A later review module will reference questions and store review events separately.

### `apps.core`

Owns application-level pages and technical endpoints that do not belong to a product domain:

- public landing page;
- dashboard composition;
- database-aware health endpoint.

The dashboard may read from domain modules to present summaries, but domain rules must remain in the owning module.

### `config`

Owns deployment and framework configuration:

- URL composition;
- WSGI and ASGI entry points;
- local, test and production settings.

## Ownership boundary

Every question belongs to one user. User-facing queries always filter by the authenticated owner. Requests for another user's question return `404` so the application does not disclose whether that record exists.

## Settings strategy

- `base.py`: settings shared by every environment.
- `local.py`: local PostgreSQL and development behaviour.
- `test.py`: PostgreSQL tests, deterministic password hashing and in-memory email.
- `production.py`: required secrets, HTTPS controls, WhiteNoise and managed PostgreSQL.

SQLite is deliberately not configured as an application environment because future PostgreSQL-specific behaviour should be exercised during development and CI.

## Future module direction

Likely later modules include:

- `reviews` for attempts, recall ratings and spaced repetition;
- `study` for review sessions and interview modes;
- `planning` for the Focus Engine;
- `goals` for lightweight interview context and deadlines;
- `analytics` for pattern mastery and coverage;
- `ai` for optional enhancement workflows.

Views coordinate HTTP requests. They should not calculate mastery, scheduling intervals or AI prompts directly.
