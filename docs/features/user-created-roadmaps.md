# User-created roadmaps

## Purpose

User-created roadmaps let a learner build a private learning path when the
built-in ViewCoach curriculum or an imported source does not match the work
they need to do.

The feature extends the existing roadmap hierarchy:

```text
Roadmap
→ Module (`RoadmapSection`)
→ Topic (`RoadmapTopic`)
→ private progress, notes, resources and evidence
```

It does not introduce a second curriculum model.

## Delivered workflow

A signed-in user can:

- create an empty private roadmap;
- choose career, skill or practice intent;
- edit roadmap metadata without changing its stable URL;
- add, edit, move and delete modules;
- add, edit, move and delete topics;
- attach an optional learning URL and time estimate to a topic;
- open the existing topic workspace for notes, resources, evidence and cards;
- opt the roadmap into or out of daily planner focus;
- delete the roadmap through an explicit destructive confirmation.

## Decisions

### Private ownership

Every user-created roadmap uses `Roadmap.Source.CUSTOM`,
`is_system=False`, and `created_by=<current user>`. Existing access rules
therefore keep it visible only to its owner.

### Stable slugs

Editing a title does not rewrite the slug. This preserves bookmarks,
planner links and topic-workspace URLs.

### Server-rendered ordering

Modules and topics use accessible Move up / Move down controls. Drag-and-drop
was rejected for this patch because it adds client-side state, keyboard and
mobile complexity without improving the core workflow.

### Explicit planner focus

Saving a roadmap does not automatically send it to the planner. A roadmap
must contain at least one topic and the user must choose **Add to planner**.

There is no new arbitrary focus limit for personal roadmaps in this patch.
The planner still applies its own candidate cap and only considers focused,
in-progress custom roadmaps.

### Destructive deletion

Deleting a topic or module removes its progress, notes, resources and
evidence links through the existing ownership graph. Generated question cards
remain user-owned, but their source topic or generation batch may be cleared.

### Stable shared backend

The feature reuses the existing roadmap detail, topic workspace, notes,
resources, question generation, goal selection and planner eligibility.
Only creation and structure management are new.

## Trade-offs

- Up/down controls are slower than drag-and-drop for very large roadmaps, but
  are deterministic, accessible and reliable on mobile.
- Blank roadmaps are allowed, which keeps creation lightweight but means they
  cannot enter planner focus until a topic exists.
- No sharing, templates, cloning, version history or collaborative editing is
  included.
- No AI-generated roadmap structure is included. RAG work remains the next
  major milestone after roadmap ownership is stable.
- Deletion is permanent. Soft deletion would preserve history but adds state
  and query complexity that is not yet justified.

## Verification

Run:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest apps/roadmaps/tests/test_custom_roadmap_services.py -q
python -m pytest apps/roadmaps/tests/test_custom_roadmap_views.py -q
python -m pytest
python -m ruff check .
python -m ruff format --check .
git diff --check
```
