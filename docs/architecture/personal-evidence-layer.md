# Personal Evidence Layer

## Purpose

Roadmaps describe general role and skill expectations. The personal evidence layer records where a user has actually applied those expectations and how they can explain the work under interview follow-up.

The layer prevents project history, technical decisions and behavioural stories from being duplicated across roadmap notes, interview goals and individual questions.

## Core model

`EvidenceItem` is the reusable private source record. It can represent a project, work experience, coursework, leadership experience or technical incident. It stores the context, problem, personal contribution, technologies, outcome, lessons and an optional supporting link.

Each evidence item may own:

- `DecisionRecord` entries for architecture and trade-off discussions;
- `BehaviouralStory` entries structured around situation, task, action, result and reflection.

## Reuse through links

Evidence is linked rather than copied:

- `TopicEvidenceProfile` stores the user's personal angle, interview explanation, evidence gap and readiness for a roadmap topic.
- `TopicEvidenceLink` attaches reusable evidence records to that profile.
- `QuestionEvidenceLink` records which real example supports an interview-question answer.
- `GoalEvidenceLink` stores goal-specific framing without changing the underlying historical record.

This separation keeps facts stable while allowing the same project to be framed differently for backend, AI-enabled software and data roles.

## Ownership boundary

Every evidence record is user-owned and private. Link forms only expose evidence owned by the authenticated user. Views validate access to the linked roadmap topic, question or interview goal before creating or removing a relationship.

Model validation also rejects cross-user links when records are created outside the normal form workflow.

## Evidence readiness

Topic evidence uses four explicit states:

1. Knowledge only
2. Project evidence
3. Work evidence
4. Interview ready

This is separate from roadmap completion. A user may understand a topic without yet having a defensible example or rehearsed explanation.

## Future extensions

The layer is intentionally deterministic and does not require AI. Later AI or RAG features may retrieve the user's approved evidence to draft practice questions, identify unsupported claims or simulate follow-up questions, but the user-owned records remain the source of truth.
