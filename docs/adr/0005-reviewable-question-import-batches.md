# ADR 0005: Reviewable, non-AI question import batches

## Status

Accepted

## Context

Creating interview questions one at a time creates avoidable setup work when users already have lists in notes, documents or PDFs. Imports are also error-prone: question boundaries may be imperfect, titles need to be generated, repeated submissions can create duplicates and document uploads should not become permanent storage.

## Decision

Introduce `QuestionImportBatch` and temporary `QuestionImportItem` records inside `apps.questions`.

- Sources: pasted text, TXT, Markdown, CSV, DOCX and text-based PDF.
- Extraction is deterministic and does not use AI.
- Users review titles, question text, inclusion and type before creation.
- Difficulty, topic, pattern and answer fields remain blank.
- Confirmation creates typed questions as `NEEDS_NOTES` in one database transaction.
- Batch locking plus an idempotency key prevents repeated confirmations from creating duplicates.
- Exact duplicates are detected against the user's library and within the batch.
- The source file, pasted source text and preview items are deleted after successful creation.
- Completed batches keep only metadata and links to the created questions.
- Scanned PDFs are rejected until OCR is introduced deliberately.

## Consequences

- Bulk setup requires substantially less repetitive input.
- Extraction mistakes remain visible and correctable before persistence.
- Temporary uploads add file-handling and cleanup responsibilities.
- Deterministic parsing will not understand every unusual document layout.
- Future AI-assisted parsing can be added behind the same review boundary without becoming required for imports.
