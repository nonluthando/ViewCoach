# Architecture overview

## Current milestone

Milestone 3.5 adds a private personal-evidence layer on top of questions, roadmaps, mock interviews, goals and the deterministic study planner. AI enhancement remains outside this boundary.

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
- progressive answer reveal;
- resumable, reviewable imports from pasted text, TXT, Markdown, CSV, DOCX and text-based PDF;
- explicit readiness validation before questions enter future review queues.

The base table stores fields shared by every question. Typed child tables store only fields meaningful to that interview format. New formats can be introduced as new child models without adding unrelated nullable columns to every existing question.

The module does not own spaced repetition or mastery. A later review module will reference questions and store review events separately.

### `apps.reviews`

Owns deterministic spaced review:

- per-user review state and due dates;
- Again, Hard, Good and Easy scheduling;
- immutable review-attempt history;
- due and upcoming queues.

### `apps.roadmaps`

Owns structured learning paths:

- built-in role, skill and practice roadmaps;
- ordered sections and topics;
- per-user roadmap and topic progress;
- private topic notes and learning resources.

### `apps.evidence`

Owns private, reusable proof from projects, work, coursework, leadership and technical incidents:

- structured evidence records;
- technical decision logs;
- behavioural STAR stories;
- personal overlays for roadmap topics;
- links from evidence to questions and interview goals.

The module stores facts once and uses link records for role-specific framing. It does not seed a user's private history into the public question or roadmap curriculum. See [`personal-evidence-layer.md`](personal-evidence-layer.md).

### `apps.planner`

Owns the daily focus workflow:

- one study plan per user and local calendar day;
- ordered, explainable recommendations;
- free-form available-time budgeting from 15 minutes to 16 hours and scalable regeneration;
- recommendation completion and study-session tracking.

The planner reads review, roadmap and question data through application services. It does not alter the scheduling rules or progress ownership of those modules. See [`adaptive-study-planner.md`](adaptive-study-planner.md).

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

- `analytics` for pattern mastery and coverage;
- `ai` for optional enhancement workflows.

Views coordinate HTTP requests. They should not calculate mastery, scheduling intervals or AI prompts directly.
