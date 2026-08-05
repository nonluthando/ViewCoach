# ProofLoop

**An adaptive interview-preparation workspace that turns learning, practice and personal experience into an explainable daily plan.**

ProofLoop is a full-stack Django application for software engineering, data and AI interview preparation.

It connects:

- learning roadmaps;
- question practice;
- spaced review;
- project and behavioural evidence;
- interview goals;
- mock interviews;
- an explainable study planner;
- a grounded RAG Help Assistant.

The repository was originally created under the working name **ViewCoach**, so some internal references still use that name.

## Core workflow

```text
Set a target
    ↓
Build knowledge
    ↓
Practise recall
    ↓
Review weak areas
    ↓
Connect personal evidence
    ↓
Complete mock interviews
    ↓
Generate the next study plan
```

## Main features

### Structured learning

- Built-in role and skill roadmaps
- User-created roadmaps
- YouTube playlist imports
- IBM SkillsBuild and external-course tracking
- Topic progress, notes and saved resources

### Question library

- Technical, concept, behavioural and debugging questions
- Type-specific forms and detail pages
- Search, filters and private user libraries
- TXT, Markdown, CSV, DOCX and text-based PDF imports
- Gemini-generated question drafts from user notes
- Duplicate detection and readiness validation

### Spaced review

- Again, Hard, Good and Easy ratings
- Due and upcoming review queues
- Deterministic interval scheduling
- Immutable review history
- Weak-area tracking

### Explainable study planner

The planner creates a daily plan using:

- overdue reviews;
- focused roadmaps;
- recent weak areas;
- evidence gaps;
- mock interviews;
- interview deadlines;
- available study time.

Tasks are selected using explainable scoring and **OR-Tools CP-SAT optimisation**, with a deterministic fallback when the optimiser is unavailable.

### Goals, evidence and mock interviews

- Multiple interview goals with one primary goal
- OA, technical, behavioural and mixed stages
- Readiness signals linked to actual progress
- Project evidence, decision records and STAR stories
- Timed mock interviews with saved answers, confidence ratings and debriefs

### Grounded RAG Help Assistant

The Help Assistant answers only from trusted project documentation.

```text
Trusted Markdown
    ↓
Heading-aware chunking
    ↓
Gemini embeddings
    ↓
PostgreSQL + pgvector
    ↓
Similarity retrieval
    ↓
Grounded answer with citations
```

It includes:

- inline source citations;
- visible source cards;
- refusal when evidence is insufficient;
- query and latency logging;
- rate limiting;
- ingestion history;
- retrieval evaluation tests.

## Architecture

ProofLoop is a modular Django monolith.

```text
apps/
├── accounts
├── core
├── questions
├── reviews
├── roadmaps
├── planner
├── interviews
├── goals
├── evidence
└── knowledge
```

Business rules live in domain services rather than templates.

Core scheduling and planning behaviour remains deterministic. AI is used only where generation or semantic retrieval adds value.

## Technology stack

- Python 3.12
- Django 5.2
- PostgreSQL 16
- pgvector
- Google Gemini
- OR-Tools CP-SAT
- Gunicorn
- WhiteNoise
- pytest
- Ruff
- GitHub Actions
- Render

## Local setup

```bash
git clone https://github.com/nonluthando/ViewCoach.git
cd ViewCoach

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
docker compose up -d postgres

python manage.py migrate
python manage.py seed_question_bank
python manage.py seed_roadmaps
python manage.py runserver
```

Optional AI features require:

```bash
export GEMINI_API_KEY=your-key
```

To ingest the trusted Help Centre documents:

```bash
python manage.py ingest_knowledge
```

## Tests

```bash
pytest
ruff check .
python manage.py makemigrations --check --dry-run
```

The CI workflow runs against PostgreSQL with pgvector.

## Useful routes

- `/project/` — project case study
- `/dashboard/` — preparation command centre
- `/questions/` — question library
- `/reviews/` — spaced review
- `/roadmaps/` — learning roadmaps
- `/plan/` — daily plan
- `/interviews/` — mock interviews
- `/goals/` — goals and readiness
- `/evidence/` — personal evidence
- `/help/` — grounded Help Assistant

## Current status

The main product workflows are implemented and connected end to end.

Current work is focused on migrating the remaining legacy pages onto the newer ProofLoop design system.

## Author

**Luthando Mbuyane**

Computer Science, Applied Statistics and Psychology graduate building software across product engineering, applied AI and decision systems.
