# Guided mock interviews

Milestone 3.3 adds deterministic, timed mock-interview sessions to ViewCoach.

## Goals

- Turn the existing question bank into realistic practice sessions.
- Reduce the setup work required before practising.
- Prioritise due reviews and recently difficult questions.
- Preserve an explainable, non-AI selection process.
- Produce a useful debrief rather than a single opaque score.

## Data model

`MockInterview` stores the user, focus, time budget and lifecycle state.

`MockInterviewItem` stores the ordered questions and the user's assessment. Question
content is snapshotted when the interview is created, so completed sessions remain
readable even when an owned question is later edited or deleted.

## Question selection

The selection service can build mixed or question-type-specific sessions.

Candidates are limited to:

- built-in questions;
- user-owned questions that are ready for review.

When a user has a ready personal copy of a built-in question, the personal copy replaces
the built-in source. Candidates receive deterministic priority bonuses for:

1. a due review state;
2. a recent Again or Hard review;
3. being part of the user's owned library;
4. not having been reviewed yet.

Mixed sessions use a fixed type sequence so the same inputs create a stable, explainable
balance across technical, conceptual, behavioural and debugging questions.

## Session workflow

1. The user chooses a focus and duration.
2. The service snapshots and orders the selected questions.
3. Opening the session starts the timer.
4. Each answer is assessed as Struggled, Partly confident, Confident or Skipped.
5. The final answer completes the interview.
6. The debrief surfaces weak questions and preserves answer notes.

The browser timer is advisory. The backend remains the source of truth for session start,
completion and elapsed time.
