# Interview goals and readiness

Milestone 3.4 adds lightweight goal context without turning ViewCoach into an application tracker.

## Product rules

- A user may keep multiple goals, but only one active goal is primary.
- Specific-opportunity goals begin at an OA or interview stage; application tracking is out of scope.
- Supported stages are OA, technical, behavioural, mixed/final and custom.
- The primary goal guides the dashboard, daily-plan roadmap preference and mock-interview defaults.
- Readiness remains deterministic and explainable. It is not an AI prediction.

## Readiness inputs

The readiness score combines five independently visible components:

- roadmap coverage: 25%
- spaced-review health: 25%
- prepared question coverage: 20%
- recent mock-interview performance: 20%
- recent study consistency: 10%

Every component exposes the evidence used to calculate it. Missing evidence produces a low score and a
specific next action instead of invented confidence.

## Ownership

Goals and stages are always scoped through the authenticated user. Mock interviews may retain a nullable
goal reference so historical sessions survive when a goal is archived or deleted.
