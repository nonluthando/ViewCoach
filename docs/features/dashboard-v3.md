# Dashboard V3

Dashboard V3 turns the ViewCoach home screen into a preparation command centre.
It does not introduce a second planner or duplicate roadmap progress.

## Data contract

`apps/core/dashboard_services.py` assembles:

- today's generated study plan and completion percentage
- up to four focused roadmaps
- the section-level journey for the first focused roadmap
- due reviews and recent review activity
- a cross-feature study streak
- the primary-goal readiness report
- interview-stage and review calendar markers
- upcoming tasks and interview stages
- evidence, STAR-story, note and resource counts

## Visual hierarchy

1. Continue today's plan
2. Focused roadmaps and learning journey
3. Today's ordered work
4. Evidence and resources
5. Calendar, upcoming items and readiness

The layout is scoped under `.dashboard-v3` so older question, roadmap,
interview and evidence pages are unaffected.

## Product boundaries

- topics are visually sequenced but never hard locked
- the streak uses real completion timestamps
- readiness remains the existing weighted readiness report
- calendar events come from existing interview stages and review states
- no XP, coins, hearts, leaderboards or JavaScript framework

## Responsive order

On mobile the page becomes:

1. welcome and plan hero
2. metrics
3. today's plan
4. learning journey
5. focused roadmaps
6. evidence
7. resources
8. calendar, upcoming and readiness
