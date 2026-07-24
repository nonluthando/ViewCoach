# Adaptive study planner

## Purpose

The planner turns ViewCoach's existing review, roadmap and question data into one bounded daily plan. Its job is to reduce the context-switching and decision overhead of deciding what to study next. It is deterministic and explainable; it does not call an AI model.

## Domain boundary

`apps.planner` owns:

- one persisted `StudyPlan` per user and local calendar day;
- ordered `StudyRecommendation` snapshots;
- `StudySession` start and end events;
- deterministic recommendation and completion services;
- the Today’s Plan interface.

It reads from `reviews`, `roadmaps` and `questions`, but it does not change their scheduling or progress rules. For example, a weak-area recommendation links back to a question without moving its spaced-review due date.

## Priority order

The first implementation uses explicit priorities:

1. due review questions;
2. the next unfinished topic in the most urgent active roadmap;
3. a question rated Again or Hard in the previous 14 days;
4. a fresh built-in technical practice question;
5. a question-library setup task when no study material exists.

Recommendations are added only while the selected time budget has room. Due reviews are grouped into one actionable item and receive the first share of the budget.

## Persistence strategy

A plan is a daily snapshot rather than a live query result. This keeps the interface stable while the user studies and records which recommendations were completed. Rebuilding the plan replaces that day's recommendations using the new time budget. An active study session must be ended before regeneration.

## Future extension points

- goal and interview-date weighting;
- explicit links between roadmap topics and questions;
- mastery and coverage analytics;
- user preference controls for practice mix;
- optional AI explanations that enhance, rather than replace, deterministic priorities.
