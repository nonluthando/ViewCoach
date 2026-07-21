# ADR-0001: Use a modular Django monolith

- **Status:** Accepted
- **Date:** 2026-07-21

## Context

The application needs authentication, relational workflows, forms, administration, deterministic learning rules, document ingestion and later RAG. It is being built by one developer and must reach deployable vertical slices quickly.

## Decision

Build one Django deployment divided into domain-focused Django apps. Keep business logic outside views and isolate external AI-provider code behind application interfaces.

## Consequences

- Deployment and local development remain simple.
- Cross-domain database transactions remain straightforward.
- Module boundaries must be enforced through code review and tests rather than network boundaries.
- A module may be extracted later only when an actual scaling or ownership reason exists.

## Rejected alternatives

- Microservices from the first release.
- Separate FastAPI service for RAG before ingestion or traffic requires it.
