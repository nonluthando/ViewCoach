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

The Help Assistant answers only from trusted project documentation, with guardrails against hallucinated or uncited answers.

```text
Trusted Markdown
    ↓
Heading-aware chunking
    ↓
Gemini embeddings
    ↓
PostgreSQL + pgvector
    ↓
Similarity retrieval (3x over-fetch + threshold filter)
    ↓
Grounded answer with [Source N] citations
```

**Reliability**

- Refuses (`NOT_SUPPORTED`) instead of guessing when retrieved evidence is empty or below the similarity threshold.
- Every citation in a generated answer is validated against the chunks actually retrieved — an out-of-range or missing `[Source N]` is treated as unsupported, never silently defaulted to "cite everything."
- The system prompt treats any instructions found inside a question or a retrieved document as data, not commands, as a defence against prompt injection.
- Ingestion is idempotent and transactional: unchanged documents are skipped by content checksum, renamed source files are re-matched by slug instead of duplicated, and chunk replacement is wrapped in `select_for_update()` so nothing reads a half-rebuilt document mid-swap.
- One `try/except` boundary wraps both retrieval and generation, so a retrieval-time failure (not just a generation-time one) is always logged and surfaced as a handled `AnswerGenerationError` rather than an unhandled exception.

**Observability**

- Every call — answered, refused, or errored — is written to a structured `KnowledgeQueryLog` row with its status, retrieved chunk IDs, citations, top similarity score, latency, and (on failure) the exception type and message.
- The same log table backs per-user rate limiting, so no separate counter store is needed.
- Query logs give an auditable record of what the assistant was asked, what it found, and why it answered or refused — not just free-text application logs.

**Evaluation**

- A hand-labelled retrieval test set scores retrieval quality with Mean Reciprocal Rank across product, interview-prep, hand-written and auto-generated documentation.
- An opt-in LLM-as-judge separately grades whether a generated answer's claims are actually supported by its retrieved context, catching hallucination a retrieval-only metric would miss.
- Retrieval quality and answer faithfulness are measured independently on purpose, so a regression in one doesn't get mistaken for a regression in the other.

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
