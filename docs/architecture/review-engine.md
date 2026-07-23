# Review Engine

Milestone 2 introduces deterministic review scheduling for user-owned questions.

## Boundary

The review module owns:

- per-user scheduling state;
- due queues;
- recall ratings;
- immutable review attempts;
- interval updates;
- review history.

The questions module continues to own question content, readiness and authorization.

## Eligibility

Only questions that:

1. belong to the authenticated user; and
2. have status `READY_FOR_REVIEW`

enter the review engine.

Review states are created lazily and idempotently when the dashboard or review queue is opened.

## Ratings

The first release uses four explicit recall ratings:

| Rating | Meaning | Initial schedule |
|---|---|---|
| Again | Could not retrieve the answer | 10 minutes |
| Hard | Retrieved with substantial effort | 1 day |
| Good | Correct recall with acceptable effort | 1 day, then 3 days |
| Easy | Immediate, confident recall | 4 days |

Later intervals use the current interval and ease factor. Again and Hard reduce ease; Easy increases it. The minimum ease factor is 1.30.

## Auditability

Every rating creates a `ReviewAttempt` containing the previous and newly scheduled due dates, intervals and ease factors. Scheduling logic is deterministic and does not depend on AI.
