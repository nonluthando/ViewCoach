# ADR 0004: Concrete base question with typed child models

## Status

Accepted

## Context

Technical, behavioural and repository-debugging questions share identity, ownership, prompt, company, status and timestamps. Their answer structures differ substantially. A single table would accumulate fields that are meaningless and null for most rows, while separate unrelated models would make a unified private library harder to query.

## Decision

Use Django multi-table inheritance:

- `Question` is the concrete base table;
- `TechnicalQuestion`, `BehaviouralQuestion` and `DebugQuestion` are child tables;
- each child save operation fixes its `question_type` discriminator;
- the base table powers common library queries and ownership checks;
- typed forms and templates operate on the child models.

Direct creation of untyped base questions is not exposed through the application or admin.

## Consequences

- Common library queries remain straightforward.
- Each question type owns only meaningful fields.
- Adding another interview format requires a child model and UI rather than widening one table.
- Reading subtype fields requires one-to-one joins.
- The application must deliberately resolve a base question to its typed child for detail and edit workflows.
