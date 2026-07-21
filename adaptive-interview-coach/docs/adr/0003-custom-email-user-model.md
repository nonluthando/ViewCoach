# ADR-0003: Create an email-based user model before the first migration

- **Status:** Accepted
- **Date:** 2026-07-21

## Context

Email is the intended login identity. Changing Django's user model after dependent tables exist requires complex manual migration work.

## Decision

Create `accounts.User` in `accounts/0001_initial.py`, remove the username field and set the unique, normalised email field as `USERNAME_FIELD`.

## Consequences

- All future relationships must reference `settings.AUTH_USER_MODEL`.
- Profile and learning data should remain outside the authentication model.
- The first migration must never be replaced by migrations based on Django's default user model.
