# Roadmap Source Separation and UI Foundation V2

## Decision

ViewCoach roadmaps and imported YouTube roadmaps share the same learning
progress infrastructure, but they are separate product experiences.

The shared engine remains:

- `Roadmap`
- `RoadmapSection`
- `RoadmapTopic`
- `UserRoadmap`
- `UserTopicProgress`
- `UserTopicResource`

Source-specific metadata and workflows remain outside the shared engine.
`Roadmap.source` identifies the owning product experience:

- `VIEWCOACH` — curated built-in curriculum
- `YOUTUBE` — user-owned imported playlists
- `IBM` — reserved for the future IBM SkillsBuild importer
- `CUSTOM` — other user imports

## Catalogue boundary

The ViewCoach catalogue returns only published, system-owned
`VIEWCOACH` records. The YouTube library queries
`YouTubePlaylistRoadmap` by the authenticated user and only accepts linked
`YOUTUBE` roadmaps.

A compatibility service still exists for internal callers that explicitly
need a combined accessible-roadmap collection. User-facing catalogue views
do not use it.

## Routes and templates

ViewCoach roadmaps use the existing routes:

- `/roadmaps/`
- `/roadmaps/<slug>/`
- `/roadmaps/<slug>/topics/<id>/`

YouTube roadmaps use source-specific routes:

- `/roadmaps/youtube/`
- `/roadmaps/youtube/<slug>/`
- `/roadmaps/youtube/<slug>/videos/<topic-id>/`

Legacy YouTube detail URLs redirect to the canonical YouTube route. Existing
mutation route names are retained as compatibility aliases where necessary.

YouTube playback is no longer conditionally embedded in the built-in topic
template. It has a dedicated video workspace containing playback, notes,
resources, evidence and progress controls.

## Access control

A YouTube roadmap is accessible only when:

1. the `YouTubePlaylistRoadmap.user` is the authenticated user;
2. its linked roadmap is published; and
3. the linked roadmap has source `YOUTUBE`.

The shared notes, resource and progress endpoints still validate roadmap
ownership before mutating data and redirect back to the correct source
workspace.

## UI foundation

The authenticated application shell now uses:

- a navy sidebar;
- blue primary actions;
- a white top bar;
- a soft grey workspace;
- rounded white cards;
- system sans-serif typography; and
- source-specific ViewCoach and YouTube markers.

The dashboard only displays values backed by existing services. It does not
invent streaks, mastery percentages or analytics that are not yet modelled.

## Future IBM integration

The reserved `IBM` source allows the IBM SkillsBuild importer to create
roadmaps without being treated as built-in curriculum or YouTube content.
IBM course notes can later feed the existing question-card generation and
review engine without creating a separate flashcard model.
