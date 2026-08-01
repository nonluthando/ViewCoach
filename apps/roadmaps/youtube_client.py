from __future__ import annotations

import html
import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from django.conf import settings

YOUTUBE_API_ROOT = "https://www.googleapis.com/youtube/v3"
PLAYLIST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{10,100}$")
ISO_DURATION_PATTERN = re.compile(
    r"^P"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?"
    r")?$"
)
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}


class YouTubeImportError(RuntimeError):
    pass


class YouTubeConfigurationError(YouTubeImportError):
    pass


class YouTubePlaylistUnavailable(YouTubeImportError):
    pass


class YouTubePlaylistTooLarge(YouTubeImportError):
    pass


@dataclass(frozen=True, slots=True)
class PlaylistVideoPreview:
    playlist_item_id: str
    video_id: str
    title: str
    channel_title: str
    thumbnail_url: str
    duration_seconds: int
    position: int
    available: bool
    embeddable: bool
    made_for_kids: bool | None

    @property
    def watch_url(self):
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @property
    def duration_display(self):
        return format_duration(self.duration_seconds)


@dataclass(frozen=True, slots=True)
class PlaylistPreview:
    playlist_id: str
    source_url: str
    title: str
    description: str
    channel_title: str
    thumbnail_url: str
    videos: tuple[PlaylistVideoPreview, ...]

    @property
    def video_count(self):
        return len(self.videos)

    @property
    def available_videos(self):
        return tuple(video for video in self.videos if video.available)

    @property
    def unavailable_videos(self):
        return tuple(video for video in self.videos if not video.available)

    @property
    def available_video_count(self):
        return len(self.available_videos)

    @property
    def unavailable_video_count(self):
        return len(self.unavailable_videos)

    @property
    def total_duration_seconds(self):
        return sum(video.duration_seconds for video in self.available_videos)

    @property
    def total_duration_display(self):
        seconds = self.total_duration_seconds
        hours, remainder = divmod(seconds, 3600)
        minutes, remaining_seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m"
        return f"{remaining_seconds}s"


def extract_playlist_id(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError("Paste a YouTube playlist link.")

    if PLAYLIST_ID_PATTERN.fullmatch(cleaned):
        return cleaned

    candidate = cleaned
    if "://" not in candidate:
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    host = parsed.hostname.lower() if parsed.hostname else ""
    if host not in YOUTUBE_HOSTS and not host.endswith(".youtube.com"):
        raise ValueError("Use a YouTube playlist link.")

    playlist_values = parse_qs(parsed.query).get("list", [])
    if not playlist_values:
        raise ValueError("That link does not contain a YouTube playlist ID.")

    playlist_id = playlist_values[0].strip()
    if not PLAYLIST_ID_PATTERN.fullmatch(playlist_id):
        raise ValueError("The YouTube playlist ID is not valid.")
    return playlist_id


def parse_iso8601_duration(value: str) -> int:
    match = ISO_DURATION_PATTERN.fullmatch((value or "").strip())
    if not match:
        raise ValueError(f"Unsupported YouTube duration: {value!r}")
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def format_duration(seconds: int) -> str:
    hours, remainder = divmod(max(0, int(seconds)), 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{remaining_seconds:02d}"
    return f"{minutes}:{remaining_seconds:02d}"


def _best_thumbnail(thumbnails: dict | None) -> str:
    thumbnails = thumbnails or {}
    for key in ("maxres", "standard", "high", "medium", "default"):
        url = (thumbnails.get(key) or {}).get("url")
        if url:
            return url
    return ""


def _batches(values: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


class YouTubeDataClient:
    def __init__(self, *, api_key: str | None = None, timeout: int = 15):
        self.api_key = (
            api_key or getattr(settings, "YOUTUBE_API_KEY", "") or os.getenv("YOUTUBE_API_KEY", "")
        )
        self.timeout = timeout
        self.max_videos = int(
            getattr(
                settings,
                "YOUTUBE_PLAYLIST_MAX_VIDEOS",
                os.getenv("YOUTUBE_PLAYLIST_MAX_VIDEOS", "250"),
            )
        )

    def _get_json(self, resource: str, **params):
        if not self.api_key:
            raise YouTubeConfigurationError(
                "YouTube playlist import is not configured yet. "
                "Add YOUTUBE_API_KEY to the server environment."
            )

        query = urlencode({**params, "key": self.api_key})
        request = Request(
            f"{YOUTUBE_API_ROOT}/{resource}?{query}",
            headers={
                "Accept": "application/json",
                "User-Agent": "ViewCoach/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            message = "YouTube could not return that playlist."
            try:
                payload = json.loads(exc.read().decode("utf-8"))
                message = payload.get("error", {}).get("message") or message
            except (ValueError, UnicodeDecodeError):
                pass
            if exc.code in {403, 404}:
                raise YouTubePlaylistUnavailable(message) from exc
            raise YouTubeImportError(message) from exc
        except URLError as exc:
            raise YouTubeImportError(
                "ViewCoach could not reach YouTube. Try again shortly."
            ) from exc

    def fetch_playlist(self, value: str) -> PlaylistPreview:
        playlist_id = extract_playlist_id(value)
        playlist_payload = self._get_json(
            "playlists",
            part="snippet,contentDetails",
            id=playlist_id,
        )
        playlist_items = playlist_payload.get("items") or []
        if not playlist_items:
            raise YouTubePlaylistUnavailable(
                "That playlist is private, unavailable or does not exist."
            )

        playlist_resource = playlist_items[0]
        playlist_snippet = playlist_resource.get("snippet") or {}
        declared_count = (playlist_resource.get("contentDetails") or {}).get("itemCount", 0)
        if declared_count and declared_count > self.max_videos:
            raise YouTubePlaylistTooLarge(
                f"This playlist has {declared_count} videos. "
                f"ViewCoach currently imports up to {self.max_videos}."
            )

        raw_items = []
        next_page_token = ""
        while True:
            request_params = {
                "part": "snippet,contentDetails,status",
                "playlistId": playlist_id,
                "maxResults": 50,
            }
            if next_page_token:
                request_params["pageToken"] = next_page_token
            page = self._get_json("playlistItems", **request_params)
            raw_items.extend(page.get("items") or [])
            if len(raw_items) > self.max_videos:
                raise YouTubePlaylistTooLarge(
                    f"ViewCoach currently imports up to {self.max_videos} videos."
                )
            next_page_token = page.get("nextPageToken") or ""
            if not next_page_token:
                break

        video_ids = []
        for item in raw_items:
            snippet = item.get("snippet") or {}
            content_details = item.get("contentDetails") or {}
            video_id = content_details.get("videoId") or (snippet.get("resourceId") or {}).get(
                "videoId"
            )
            if video_id and video_id not in video_ids:
                video_ids.append(video_id)

        details_by_id = {}
        for batch in _batches(video_ids, 50):
            video_page = self._get_json(
                "videos",
                part="snippet,contentDetails,status",
                id=",".join(batch),
            )
            for video in video_page.get("items") or []:
                details_by_id[video["id"]] = video

        videos = []
        for fallback_position, item in enumerate(raw_items):
            snippet = item.get("snippet") or {}
            content_details = item.get("contentDetails") or {}
            item_status = item.get("status") or {}
            position = snippet.get("position", fallback_position)
            video_id = (
                content_details.get("videoId")
                or (snippet.get("resourceId") or {}).get("videoId")
                or f"unavailable-{position}"
            )
            playlist_item_id = item.get("id") or f"missing-{position}-{video_id}"
            detail = details_by_id.get(video_id)
            detail_snippet = (detail or {}).get("snippet") or {}
            detail_status = (detail or {}).get("status") or {}
            detail_content = (detail or {}).get("contentDetails") or {}

            privacy_status = (
                detail_status.get("privacyStatus") or item_status.get("privacyStatus") or ""
            )
            upload_status = detail_status.get("uploadStatus", "processed")
            available = (
                bool(detail) and privacy_status != "private" and upload_status == "processed"
            )
            embeddable = available and bool(detail_status.get("embeddable", False))
            made_for_kids = detail_status.get("madeForKids")
            duration_seconds = 0
            duration_value = detail_content.get("duration")
            if available and duration_value:
                duration_seconds = parse_iso8601_duration(duration_value)

            title = html.unescape(
                detail_snippet.get("title") or snippet.get("title") or "Unavailable video"
            ).strip()
            if title in {"Private video", "Deleted video"}:
                available = False
                embeddable = False

            videos.append(
                PlaylistVideoPreview(
                    playlist_item_id=playlist_item_id,
                    video_id=video_id,
                    title=title,
                    channel_title=(
                        detail_snippet.get("channelTitle")
                        or snippet.get("videoOwnerChannelTitle")
                        or playlist_snippet.get("channelTitle")
                        or ""
                    ),
                    thumbnail_url=_best_thumbnail(
                        detail_snippet.get("thumbnails") or snippet.get("thumbnails")
                    ),
                    duration_seconds=duration_seconds,
                    position=int(position),
                    available=available,
                    embeddable=embeddable,
                    made_for_kids=made_for_kids,
                )
            )

        videos.sort(key=lambda video: (video.position, video.playlist_item_id))
        return PlaylistPreview(
            playlist_id=playlist_id,
            source_url=f"https://www.youtube.com/playlist?list={playlist_id}",
            title=html.unescape(playlist_snippet.get("title") or "YouTube playlist").strip(),
            description=html.unescape(playlist_snippet.get("description") or "").strip(),
            channel_title=html.unescape(playlist_snippet.get("channelTitle") or "").strip(),
            thumbnail_url=_best_thumbnail(playlist_snippet.get("thumbnails")),
            videos=tuple(videos),
        )
