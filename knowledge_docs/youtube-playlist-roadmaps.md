# YouTube Playlist Roadmaps

YouTube Playlist Roadmaps let a signed-in user turn an accessible YouTube playlist into a ViewCoach skill roadmap.

## Import flow

Open Roadmaps and choose **Import YouTube playlist**. Paste a YouTube playlist URL and preview the course before creating it.

The preview shows:

- playlist title and channel
- available video count
- total video length
- video titles, thumbnails and durations
- videos that are unavailable
- videos that cannot be embedded and must open on YouTube

When the user confirms the import, ViewCoach creates one user-owned skill roadmap. The playlist becomes a roadmap section and each available video becomes a roadmap topic in the original playlist order.

## Video workspace

A YouTube topic uses the normal roadmap topic workspace. It adds:

- an embedded YouTube player when embedding is permitted
- a direct link to the video on YouTube
- the video duration and channel
- study notes
- roadmap progress controls
- a **Mark watched and continue** action

Completion is manual. ViewCoach does not claim that a video was watched merely because the embedded player loaded or played.

If embedding is disabled, the user can watch the video on YouTube and return to mark it complete.

## Duplicate handling

A user can import a particular YouTube playlist only once. If the same playlist is submitted again, ViewCoach links to the existing roadmap instead of creating a duplicate.

Different users can import the same playlist into their own accounts.

## Unavailable videos

Private, deleted or inaccessible videos are shown in the import preview but are not created as new roadmap topics.

If an imported video later becomes unavailable, ViewCoach keeps the existing topic so the user's notes and progress are not silently deleted. The topic displays an unavailable state.


## Removing an imported roadmap

The owner can remove an imported YouTube roadmap from ViewCoach. This deletes the ViewCoach roadmap, its stored YouTube metadata and its associated ViewCoach progress data. It does not delete or modify the original playlist on YouTube.

## Synchronisation

YouTube metadata can change after import. ViewCoach stores the last synchronisation time and provides:

```bash
python manage.py sync_youtube_playlists
```

The command refreshes stale playlist metadata, video availability, duration, embedding permission, title and order. Run it at least every 30 days.

Use `--all` to refresh every playlist or `--playlist-id` to refresh one playlist.

## Current scope

The first milestone supports accessible playlists through a server-side YouTube Data API key. It does not connect to a user's YouTube account and does not import private playlists that require OAuth.

Planner scheduling, calendar blocks, playlist editing, transcript-based questions and AI-generated course summaries are later milestones.
