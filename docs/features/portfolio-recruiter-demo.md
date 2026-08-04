# Recruiter portfolio demo

## Journey

```text
Public landing page
→ project case study
→ create isolated temporary workspace
→ guided eight-step tour
→ reset or delete workspace
```

## Included demo data

- user-created roadmap with modules, topics, notes, resources and progress
- favourite YouTube roadmap with video metadata and progress
- technical, concept, behavioural and debugging questions
- spaced-review states and review history
- three evidence items
- project explanations
- architecture decision record
- interview-ready STAR story
- topic, question and goal evidence links
- active interview goal with stages
- completed mixed mock interview

## Safety

- demo creation uses POST and CSRF protection
- each visitor receives a separate user with an unusable password
- live AI generation and external imports are blocked
- demo responses use `Cache-Control: no-store`
- a capacity limit prevents unlimited active demo accounts
- reset and end actions delete the old account
- an expiry command removes abandoned accounts

## Environment

```text
PORTFOLIO_DEMO_ENABLED=true
PORTFOLIO_DEMO_SESSION_SECONDS=7200
PORTFOLIO_DEMO_TTL_HOURS=24
PORTFOLIO_DEMO_MAX_ACTIVE=25
```

## Cleanup

Run periodically:

```bash
python manage.py cleanup_portfolio_demo_users
```

Delete every demo account during maintenance:

```bash
python manage.py cleanup_portfolio_demo_users --all
```

## Decision

The implementation uses isolated temporary accounts rather than one shared
credential. This costs more database rows, but protects the recruiter experience
from previous visitors' edits and makes reset behaviour deterministic.
