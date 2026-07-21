# ADR-0002: Use PostgreSQL in development, testing and production

- **Status:** Accepted
- **Date:** 2026-07-21

## Context

Later milestones require pgvector, PostgreSQL indexes and database constraints. SQLite would allow development and CI behaviour to diverge from production.

## Decision

Use PostgreSQL in every environment. The local database is supplied through Docker Compose, CI uses a PostgreSQL service container and production uses managed PostgreSQL.

## Consequences

- Local setup requires PostgreSQL or Docker.
- Database-specific behaviour is exercised early.
- Test failures are more representative of production.

## Rejected alternatives

- SQLite for development and tests.
- A second database dedicated to vector retrieval.
