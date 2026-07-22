# ADR 0006: Shared system question library with private user state

## Status
Accepted

## Context
ViewCoach must be useful immediately after registration. Copying the full starter bank into every account would duplicate content, make corrections difficult, and increase storage. Built-in answers must remain curated and read-only while users retain private notes and progress.

## Decision
A `Question` can be system-owned (`is_system=True`, no user owner, stable `system_key`) or user-owned. System questions are shared by all users. `UserQuestionState` stores bookmark and progress state, while `UserQuestionNote` stores private notes separately from the canonical answer. The starter bank is stored as validated JSON and loaded idempotently by `seed_question_bank` during deployment.

## Consequences
- Canonical corrections update one shared record.
- User notes and progress remain private.
- Built-in questions cannot be edited or deleted through user routes.
- The deployment process must run the idempotent seed command after migrations.
- Future question-bank batches can reuse the same stable-key import pipeline.
