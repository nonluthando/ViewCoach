# ViewCoach YouTube Playlist Roadmaps: Milestone 1

This package is based on the `main` branch after the RAG merge commit:

`b6d8d571897285f4d5bc0a61852b4ce44290e0c2`

## Included

- accessible YouTube playlist URL validation
- playlist preview
- title, channel, thumbnail, duration and order import
- unavailable and non-embeddable video handling
- user-owned ViewCoach skill roadmap creation
- embedded privacy-enhanced YouTube player
- manual **Mark watched and continue**
- duplicate prevention per user
- metadata refresh command
- Django Admin integration
- tests
- trusted RAG product documentation
- engineering decision and trade-off notes

## Required environment variable

Create a Google Cloud API key with YouTube Data API v3 enabled, then add:

```text
YOUTUBE_API_KEY=...
YOUTUBE_PLAYLIST_MAX_VIDEOS=250
```

Keep the key server-side and restrict it to YouTube Data API v3.

## Upload

Upload the files using the paths in `UPLOAD_MANIFEST.json`.

Do not put the migration under another app. It belongs at:

```text
apps/roadmaps/migrations/0003_youtube_playlist_roadmaps.py
```

## Deploy

The normal deployment migration command should apply the new schema:

```bash
python manage.py migrate
```

The RAG build ingestion command will also discover:

```text
knowledge_docs/product/youtube-playlist-roadmaps.md
```

## YouTube metadata refresh

Schedule this at least every 30 days:

```bash
python manage.py sync_youtube_playlists
```

For testing:

```bash
python manage.py sync_youtube_playlists --all
```

## Milestone boundary

This package does not yet add playlist videos to the daily planner or calendar. That is the next YouTube milestone after the import, playback and progress flow is verified.
