#!/usr/bin/env python3
"""Apply ViewCoach Patch 3A: roadmap focus controls and YouTube groups.

Run from the repository root after Patch 2B. The script is intentionally
idempotent for the markers it owns and refuses to continue when the expected
repository shape cannot be found.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()


def require(path: str) -> Path:
    target = ROOT / path
    if not target.exists():
        raise SystemExit(f"Missing expected repository file: {path}")
    return target


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"Could not locate marker for {label}. No files were written.")
    return text.replace(old, new, 1)


def insert_before(text: str, marker: str, addition: str, *, label: str) -> str:
    if addition.strip() in text:
        return text
    if marker not in text:
        raise SystemExit(f"Could not locate marker for {label}. No files were written.")
    return text.replace(marker, addition + marker, 1)


def append_once(text: str, addition: str) -> str:
    if addition.strip() in text:
        return text
    return text.rstrip() + "\n\n" + addition.strip() + "\n"


paths = {
    "models": require("apps/roadmaps/models.py"),
    "services": require("apps/roadmaps/services.py"),
    "views": require("apps/roadmaps/views.py"),
    "youtube_views": require("apps/roadmaps/youtube_views.py"),
    "urls": require("apps/roadmaps/urls.py"),
    "youtube_forms": require("apps/roadmaps/youtube_forms.py"),
    "youtube_services": require("apps/roadmaps/youtube_services.py"),
    "planner": require("apps/planner/candidate_builders.py"),
    "reviews": require("apps/reviews/services.py"),
    "core_views": require("apps/core/views.py"),
    "roadmap_list": require("templates/roadmaps/roadmap_list.html"),
    "roadmap_detail": require("templates/roadmaps/roadmap_detail.html"),
    "youtube_list": require("templates/roadmaps/youtube/youtube_roadmap_list.html"),
    "css": require("static/css/roadmaps.css"),
}
changes = {key: path.read_text() for key, path in paths.items()}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
changes["models"] = replace_once(
    changes["models"],
    """    target_date = models.DateField(null=True, blank=True)\n""",
    """    is_focused = models.BooleanField(default=False)\n    target_date = models.DateField(null=True, blank=True)\n""",
    label="UserRoadmap focus field",
)
changes["models"] = replace_once(
    changes["models"],
    """        indexes = [\n            models.Index(fields=[\"user\", \"status\"], name=\"user_roadmap_status_idx\"),\n        ]\n""",
    """        indexes = [\n            models.Index(fields=[\"user\", \"status\"], name=\"user_roadmap_status_idx\"),\n            models.Index(fields=[\"user\", \"is_focused\"], name=\"user_roadmap_focus_idx\"),\n        ]\n""",
    label="UserRoadmap focus index",
)

group_model = """
class YouTubeRoadmapGroup(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="youtube_roadmap_groups",
    )
    name = models.CharField(max_length=80)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "name", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_user_youtube_group_name",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "position"],
                name="yt_group_user_position_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user}: {self.name}"


"""
changes["models"] = insert_before(
    changes["models"],
    "class YouTubePlaylistRoadmap(models.Model):\n",
    group_model,
    label="YouTubeRoadmapGroup model",
)
changes["models"] = replace_once(
    changes["models"],
    """    playlist_id = models.CharField(max_length=100)\n""",
    """    group = models.ForeignKey(\n        YouTubeRoadmapGroup,\n        on_delete=models.SET_NULL,\n        related_name=\"roadmaps\",\n        null=True,\n        blank=True,\n    )\n    is_favourite = models.BooleanField(default=False)\n    playlist_id = models.CharField(max_length=100)\n""",
    label="YouTube group and favourite fields",
)
changes["models"] = replace_once(
    changes["models"],
    """            models.Index(\n                fields=[\"user\", \"last_synced_at\"],\n                name=\"yt_playlist_user_sync_idx\",\n            ),\n""",
    """            models.Index(\n                fields=[\"user\", \"last_synced_at\"],\n                name=\"yt_playlist_user_sync_idx\",\n            ),\n            models.Index(\n                fields=[\"user\", \"is_favourite\"],\n                name=\"yt_playlist_user_fav_idx\",\n            ),\n""",
    label="YouTube favourite index",
)

# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------
changes["youtube_forms"] = append_once(
    changes["youtube_forms"],
    """

class YouTubeRoadmapGroupForm(forms.Form):
    name = forms.CharField(
        max_length=80,
        label="Group name",
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. Backend development",
                "autocomplete": "off",
            }
        ),
    )

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())
""",
)

# ---------------------------------------------------------------------------
# Roadmap services and limits
# ---------------------------------------------------------------------------
changes["services"] = replace_once(
    changes["services"],
    "from django.db.models import Count, Q\n",
    "from django.db import transaction\nfrom django.db.models import Count, Q\n",
    label="roadmap service transaction import",
)
changes["services"] = replace_once(
    changes["services"],
    """    YouTubePlaylistRoadmap,\n)\n""",
    """    YouTubePlaylistRoadmap,\n    YouTubeRoadmapGroup,\n)\n""",
    label="roadmap service group import",
)
limit_services = """
MAX_FOCUSED_VIEWCOACH_ROADMAPS = 4
MAX_FAVOURITE_YOUTUBE_ROADMAPS = 5


class RoadmapSelectionLimitError(ValueError):
    pass


@transaction.atomic
def set_viewcoach_roadmap_focus(*, user, roadmap, focused: bool):
    if roadmap.source != Roadmap.Source.VIEWCOACH or not roadmap.is_system:
        raise ValueError("Only built-in ViewCoach roadmaps can be focused.")

    list(
        UserRoadmap.objects.select_for_update()
        .filter(user=user, roadmap__source=Roadmap.Source.VIEWCOACH)
        .values_list("pk", flat=True)
    )
    enrolment, _ = UserRoadmap.objects.get_or_create(
        user=user,
        roadmap=roadmap,
    )
    if focused and enrolment.status == UserRoadmap.Status.COMPLETED:
        raise ValueError(
            "Completed roadmaps cannot be focused. Mark a topic as learning first "
            "if you want to revisit the roadmap."
        )
    if focused and not enrolment.is_focused:
        focused_count = UserRoadmap.objects.filter(
            user=user,
            roadmap__source=Roadmap.Source.VIEWCOACH,
            is_focused=True,
        ).exclude(pk=enrolment.pk).count()
        if focused_count >= MAX_FOCUSED_VIEWCOACH_ROADMAPS:
            raise RoadmapSelectionLimitError(
                "You already have four focused ViewCoach roadmaps. "
                "Remove one from focus before adding another."
            )
        enrolment.is_focused = True
        if enrolment.status == UserRoadmap.Status.NOT_STARTED:
            enrolment.status = UserRoadmap.Status.IN_PROGRESS
            enrolment.started_at = enrolment.started_at or timezone.now()
    elif not focused:
        enrolment.is_focused = False

    enrolment.save(
        update_fields=[
            "is_focused",
            "status",
            "started_at",
            "updated_at",
        ]
    )
    return enrolment


@transaction.atomic
def set_youtube_roadmap_favourite(*, user, source, favourite: bool):
    list(
        YouTubePlaylistRoadmap.objects.select_for_update()
        .filter(user=user)
        .values_list("pk", flat=True)
    )
    locked = YouTubePlaylistRoadmap.objects.select_related("roadmap").get(
        pk=source.pk,
        user=user,
        roadmap__source=Roadmap.Source.YOUTUBE,
    )
    if favourite and not locked.is_favourite:
        favourite_count = YouTubePlaylistRoadmap.objects.filter(
            user=user,
            is_favourite=True,
            roadmap__source=Roadmap.Source.YOUTUBE,
        ).exclude(pk=locked.pk).count()
        if favourite_count >= MAX_FAVOURITE_YOUTUBE_ROADMAPS:
            raise RoadmapSelectionLimitError(
                "You already have five favourite YouTube roadmaps. "
                "Unfavourite one before adding another."
            )
        locked.is_favourite = True
    elif not favourite:
        locked.is_favourite = False

    locked.save(update_fields=["is_favourite", "updated_at"])
    return locked


"""
changes["services"] = insert_before(
    changes["services"],
    "def progress_summary_for_user(*, user, roadmap_ids=None):\n",
    limit_services,
    label="roadmap selection services",
)
changes["services"] = replace_once(
    changes["services"],
    """    if all_completed:\n        user_roadmap.status = UserRoadmap.Status.COMPLETED\n        user_roadmap.started_at = user_roadmap.started_at or now\n        user_roadmap.completed_at = user_roadmap.completed_at or now\n""",
    """    if all_completed:\n        user_roadmap.status = UserRoadmap.Status.COMPLETED\n        user_roadmap.started_at = user_roadmap.started_at or now\n        user_roadmap.completed_at = user_roadmap.completed_at or now\n        if roadmap.source == Roadmap.Source.VIEWCOACH:\n            user_roadmap.is_focused = False\n""",
    label="completed roadmap focus release",
)
changes["services"] = replace_once(
    changes["services"],
    """    user_roadmap.save(update_fields=[\"status\", \"started_at\", \"completed_at\", \"updated_at\"])\n""",
    """    user_roadmap.save(\n        update_fields=[\n            \"status\",\n            \"is_focused\",\n            \"started_at\",\n            \"completed_at\",\n            \"updated_at\",\n        ]\n    )\n""",
    label="sync focus field",
)
changes["services"] = replace_once(
    changes["services"],
    "def youtube_roadmap_cards(*, user):\n",
    "def youtube_roadmap_cards(*, user, favourites_only=False):\n",
    label="YouTube card favourites option",
)
changes["services"] = replace_once(
    changes["services"],
    """    sources = list(\n        YouTubePlaylistRoadmap.objects.filter(\n            user=user,\n            roadmap__source=Roadmap.Source.YOUTUBE,\n            roadmap__is_published=True,\n        )\n        .select_related(\"roadmap\")\n        .prefetch_related(\"roadmap__sections__topics\")\n        .order_by(\"-updated_at\", \"-pk\")\n    )\n""",
    """    sources_query = YouTubePlaylistRoadmap.objects.filter(\n        user=user,\n        roadmap__source=Roadmap.Source.YOUTUBE,\n        roadmap__is_published=True,\n    )\n    if favourites_only:\n        sources_query = sources_query.filter(is_favourite=True)\n    sources = list(\n        sources_query\n        .select_related(\"roadmap\", \"group\")\n        .prefetch_related(\"roadmap__sections__topics\")\n        .order_by(\"-is_favourite\", \"group__position\", \"group__name\", \"-updated_at\", \"-pk\")\n    )\n""",
    label="YouTube card grouped query",
)
changes["services"] = append_once(
    changes["services"],
    """


def grouped_youtube_roadmap_cards(*, user):
    rows = youtube_roadmap_cards(user=user)
    rows_by_group = defaultdict(list)
    for row in rows:
        rows_by_group[row["youtube_source"].group_id].append(row)

    groups = list(
        YouTubeRoadmapGroup.objects.filter(user=user).order_by(
            "position",
            "name",
            "pk",
        )
    )
    result = [
        {
            "group": group,
            "label": group.name,
            "items": rows_by_group.pop(group.pk, []),
        }
        for group in groups
    ]
    ungrouped = rows_by_group.pop(None, [])
    if ungrouped:
        result.append(
            {
                "group": None,
                "label": "Ungrouped",
                "items": ungrouped,
            }
        )
    return result
""",
)

# ---------------------------------------------------------------------------
# Built-in roadmap views
# ---------------------------------------------------------------------------
changes["views"] = replace_once(
    changes["views"],
    """    grouped_viewcoach_roadmap_cards,\n    roadmap_progress,\n    sync_user_roadmap,\n)\n""",
    """    MAX_FOCUSED_VIEWCOACH_ROADMAPS,\n    RoadmapSelectionLimitError,\n    grouped_viewcoach_roadmap_cards,\n    roadmap_progress,\n    set_viewcoach_roadmap_focus,\n    sync_user_roadmap,\n)\n""",
    label="built-in focus service imports",
)
changes["views"] = replace_once(
    changes["views"],
    """        {\"roadmap_groups\": grouped_viewcoach_roadmap_cards(user=request.user)},\n""",
    """        {\n            \"roadmap_groups\": grouped_viewcoach_roadmap_cards(user=request.user),\n            \"focused_count\": UserRoadmap.objects.filter(\n                user=request.user,\n                roadmap__source=Roadmap.Source.VIEWCOACH,\n                is_focused=True,\n            ).count(),\n            \"focused_limit\": MAX_FOCUSED_VIEWCOACH_ROADMAPS,\n        },\n""",
    label="built-in list focus context",
)
changes["views"] = replace_once(
    changes["views"],
    """            \"progress\": roadmap_progress(user=request.user, roadmap=roadmap),\n""",
    """            \"progress\": roadmap_progress(user=request.user, roadmap=roadmap),\n            \"focused_count\": UserRoadmap.objects.filter(\n                user=request.user,\n                roadmap__source=Roadmap.Source.VIEWCOACH,\n                is_focused=True,\n            ).count(),\n            \"focused_limit\": MAX_FOCUSED_VIEWCOACH_ROADMAPS,\n""",
    label="built-in detail focus context",
)
start_focus = """
    if roadmap.source == Roadmap.Source.VIEWCOACH:
        try:
            set_viewcoach_roadmap_focus(
                user=request.user,
                roadmap=roadmap,
                focused=True,
            )
        except RoadmapSelectionLimitError as exc:
            messages.warning(request, str(exc))
        else:
            messages.success(
                request,
                f"{roadmap.title} is now one of your focused roadmaps.",
            )
        return redirect(_roadmap_detail_route(roadmap), slug=roadmap.slug)

"""
changes["views"] = insert_before(
    changes["views"],
    "    user_roadmap, created = UserRoadmap.objects.get_or_create(\n",
    start_focus,
    label="start roadmap focus branch",
)
focus_view = """

@login_required
@require_POST
def toggle_roadmap_focus(request, slug):
    roadmap = _accessible_roadmap(request.user, slug)
    focused = request.POST.get("focused") == "true"
    try:
        enrolment = set_viewcoach_roadmap_focus(
            user=request.user,
            roadmap=roadmap,
            focused=focused,
        )
    except RoadmapSelectionLimitError as exc:
        messages.warning(request, str(exc))
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        if enrolment.is_focused:
            messages.success(request, f"{roadmap.title} added to your focus list.")
        else:
            messages.info(request, f"{roadmap.title} removed from your focus list.")
    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect(_roadmap_detail_route(roadmap), slug=roadmap.slug)


"""
changes["views"] = insert_before(
    changes["views"],
    "@login_required\n@require_POST\ndef update_topic_status",
    focus_view,
    label="toggle built-in focus view",
)

# ---------------------------------------------------------------------------
# YouTube views and group operations
# ---------------------------------------------------------------------------
changes["youtube_views"] = replace_once(
    changes["youtube_views"],
    "from django.shortcuts import get_object_or_404, redirect, render\n",
    "from django.db.models import Max\nfrom django.shortcuts import get_object_or_404, redirect, render\n",
    label="YouTube Max import",
)
changes["youtube_views"] = replace_once(
    changes["youtube_views"],
    """    YouTubePlaylistRoadmap,\n    YouTubePlaylistVideo,\n)\n""",
    """    YouTubePlaylistRoadmap,\n    YouTubePlaylistVideo,\n    YouTubeRoadmapGroup,\n)\n""",
    label="YouTube group model import",
)
changes["youtube_views"] = replace_once(
    changes["youtube_views"],
    "from .services import roadmap_progress, sync_user_roadmap, youtube_roadmap_cards\n",
    """from .services import (\n    MAX_FAVOURITE_YOUTUBE_ROADMAPS,\n    RoadmapSelectionLimitError,\n    grouped_youtube_roadmap_cards,\n    roadmap_progress,\n    set_youtube_roadmap_favourite,\n    sync_user_roadmap,\n    youtube_roadmap_cards,\n)\n""",
    label="YouTube selection service imports",
)
changes["youtube_views"] = replace_once(
    changes["youtube_views"],
    "from .youtube_forms import YouTubePlaylistImportForm\n",
    "from .youtube_forms import YouTubePlaylistImportForm, YouTubeRoadmapGroupForm\n",
    label="YouTube group form import",
)
changes["youtube_views"] = replace_once(
    changes["youtube_views"],
    """        {\"youtube_roadmaps\": youtube_roadmap_cards(user=request.user)},\n""",
    """        {\n            \"youtube_roadmaps\": youtube_roadmap_cards(user=request.user),\n            \"youtube_groups\": grouped_youtube_roadmap_cards(user=request.user),\n            \"group_choices\": YouTubeRoadmapGroup.objects.filter(\n                user=request.user,\n            ).order_by(\"position\", \"name\", \"pk\"),\n            \"group_form\": YouTubeRoadmapGroupForm(),\n            \"favourite_count\": YouTubePlaylistRoadmap.objects.filter(\n                user=request.user,\n                roadmap__source=Roadmap.Source.YOUTUBE,\n                is_favourite=True,\n            ).count(),\n            \"favourite_limit\": MAX_FAVOURITE_YOUTUBE_ROADMAPS,\n        },\n""",
    label="YouTube grouped list context",
)
youtube_group_views = """

@login_required
@require_POST
def create_youtube_group(request):
    form = YouTubeRoadmapGroupForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a group name.")
        return redirect("roadmaps:youtube_list")

    name = form.cleaned_data["name"]
    if YouTubeRoadmapGroup.objects.filter(user=request.user, name__iexact=name).exists():
        messages.info(request, "A YouTube group with that name already exists.")
        return redirect("roadmaps:youtube_list")

    next_position = (
        YouTubeRoadmapGroup.objects.filter(user=request.user).aggregate(
            highest=Max("position")
        )["highest"]
        or 0
    ) + 1
    YouTubeRoadmapGroup.objects.create(
        user=request.user,
        name=name,
        position=next_position,
    )
    messages.success(request, f"Created the {name} group.")
    return redirect("roadmaps:youtube_list")


@login_required
@require_POST
def rename_youtube_group(request, group_id):
    group = get_object_or_404(YouTubeRoadmapGroup, pk=group_id, user=request.user)
    form = YouTubeRoadmapGroupForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a group name.")
        return redirect("roadmaps:youtube_list")

    name = form.cleaned_data["name"]
    if (
        YouTubeRoadmapGroup.objects.filter(user=request.user, name__iexact=name)
        .exclude(pk=group.pk)
        .exists()
    ):
        messages.info(request, "A YouTube group with that name already exists.")
        return redirect("roadmaps:youtube_list")

    group.name = name
    group.save(update_fields=["name", "updated_at"])
    messages.success(request, "YouTube group renamed.")
    return redirect("roadmaps:youtube_list")


@login_required
@require_POST
def delete_youtube_group(request, group_id):
    group = get_object_or_404(YouTubeRoadmapGroup, pk=group_id, user=request.user)
    name = group.name
    group.delete()
    messages.info(
        request,
        f"Deleted {name}. Its playlists were moved to Ungrouped.",
    )
    return redirect("roadmaps:youtube_list")


@login_required
@require_POST
def move_youtube_roadmap(request, slug):
    source = _youtube_source_for_user(request.user, slug)
    group_id = request.POST.get("group_id", "").strip()
    if group_id:
        group = get_object_or_404(
            YouTubeRoadmapGroup,
            pk=group_id,
            user=request.user,
        )
    else:
        group = None
    source.group = group
    source.save(update_fields=["group", "updated_at"])
    messages.success(request, "YouTube roadmap moved.")
    return redirect("roadmaps:youtube_list")


@login_required
@require_POST
def toggle_youtube_favourite(request, slug):
    source = _youtube_source_for_user(request.user, slug)
    favourite = request.POST.get("favourite") == "true"
    try:
        source = set_youtube_roadmap_favourite(
            user=request.user,
            source=source,
            favourite=favourite,
        )
    except RoadmapSelectionLimitError as exc:
        messages.warning(request, str(exc))
    else:
        if source.is_favourite:
            messages.success(request, f"{source.roadmap.title} added to favourites.")
        else:
            messages.info(request, f"{source.roadmap.title} removed from favourites.")
    return redirect(request.POST.get("next") or "roadmaps:youtube_list")


"""
changes["youtube_views"] = insert_before(
    changes["youtube_views"],
    "@login_required\n@require_http_methods([\"GET\", \"POST\"])\ndef youtube_playlist_import",
    youtube_group_views,
    label="YouTube group and favourite views",
)

# ---------------------------------------------------------------------------
# YouTube import defaults to favourite while capacity exists
# ---------------------------------------------------------------------------
changes["youtube_services"] = replace_once(
    changes["youtube_services"],
    "from .youtube_client import PlaylistPreview, PlaylistVideoPreview, format_duration\n",
    """from .services import MAX_FAVOURITE_YOUTUBE_ROADMAPS\nfrom .youtube_client import PlaylistPreview, PlaylistVideoPreview, format_duration\n""",
    label="YouTube favourite limit import",
)
changes["youtube_services"] = insert_before(
    changes["youtube_services"],
    "    roadmap = Roadmap.objects.create(\n",
    """    should_favourite = (\n        YouTubePlaylistRoadmap.objects.filter(\n            user=user,\n            is_favourite=True,\n            roadmap__source=Roadmap.Source.YOUTUBE,\n        ).count()\n        < MAX_FAVOURITE_YOUTUBE_ROADMAPS\n    )\n\n""",
    label="YouTube automatic favourite decision",
)
changes["youtube_services"] = replace_once(
    changes["youtube_services"],
    """        roadmap=roadmap,\n        playlist_id=preview.playlist_id,\n""",
    """        roadmap=roadmap,\n        is_favourite=should_favourite,\n        playlist_id=preview.playlist_id,\n""",
    label="YouTube automatic favourite field",
)

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
changes["urls"] = insert_before(
    changes["urls"],
    "    path(\n        \"youtube/import/confirm/\",\n",
    """    path(\n        \"youtube/groups/create/\",\n        youtube_views.create_youtube_group,\n        name=\"youtube_group_create\",\n    ),\n    path(\n        \"youtube/groups/<int:group_id>/rename/\",\n        youtube_views.rename_youtube_group,\n        name=\"youtube_group_rename\",\n    ),\n    path(\n        \"youtube/groups/<int:group_id>/delete/\",\n        youtube_views.delete_youtube_group,\n        name=\"youtube_group_delete\",\n    ),\n""",
    label="YouTube group URLs",
)
changes["urls"] = insert_before(
    changes["urls"],
    "    path(\n        \"youtube/<slug:slug>/videos/<int:topic_id>/complete/\",\n",
    """    path(\n        \"youtube/<slug:slug>/favourite/\",\n        youtube_views.toggle_youtube_favourite,\n        name=\"youtube_favourite\",\n    ),\n    path(\n        \"youtube/<slug:slug>/move/\",\n        youtube_views.move_youtube_roadmap,\n        name=\"youtube_move\",\n    ),\n""",
    label="YouTube favourite and move URLs",
)
changes["urls"] = insert_before(
    changes["urls"],
    "    path(\"<slug:slug>/\", views.roadmap_detail, name=\"detail\"),\n",
    """    path(\n        \"<slug:slug>/focus/\",\n        views.toggle_roadmap_focus,\n        name=\"focus\",\n    ),\n""",
    label="ViewCoach focus URL",
)

# ---------------------------------------------------------------------------
# Planner: only selected roadmaps can produce roadmap work
# ---------------------------------------------------------------------------
changes["planner"] = replace_once(
    changes["planner"],
    "from django.utils import timezone\n",
    "from django.db.models import Q\nfrom django.utils import timezone\n",
    label="planner Q import",
)
changes["planner"] = replace_once(
    changes["planner"],
    "from apps.roadmaps.models import RoadmapTopic, UserRoadmap, UserTopicProgress\n",
    "from apps.roadmaps.models import Roadmap, RoadmapTopic, UserRoadmap, UserTopicProgress\n",
    label="planner Roadmap import",
)
changes["planner"] = replace_once(
    changes["planner"],
    """    enrolment_query = UserRoadmap.objects.filter(\n        user=user,\n        status=UserRoadmap.Status.IN_PROGRESS,\n        roadmap__is_published=True,\n    ).select_related(\"roadmap\")\n""",
    """    enrolment_query = (\n        UserRoadmap.objects.filter(\n            user=user,\n            status=UserRoadmap.Status.IN_PROGRESS,\n            roadmap__is_published=True,\n        )\n        .filter(\n            Q(\n                roadmap__source=Roadmap.Source.VIEWCOACH,\n                is_focused=True,\n            )\n            | Q(\n                roadmap__source=Roadmap.Source.YOUTUBE,\n                roadmap__youtube_playlist__user=user,\n                roadmap__youtube_playlist__is_favourite=True,\n            )\n            | Q(\n                roadmap__source__in=[Roadmap.Source.IBM, Roadmap.Source.CUSTOM],\n                is_focused=True,\n            )\n        )\n        .select_related(\"roadmap\")\n        .distinct()\n    )\n""",
    label="planner selected-roadmap filter",
)

# ---------------------------------------------------------------------------
# Reviews: generated cards from paused/unfavourited roadmaps stay out of the
# automatic queue while ordinary user questions remain eligible.
# ---------------------------------------------------------------------------
changes["reviews"] = replace_once(
    changes["reviews"],
    "from django.db import transaction\n",
    "from django.db import transaction\nfrom django.db.models import Q\n",
    label="review Q import",
)
changes["reviews"] = replace_once(
    changes["reviews"],
    "from apps.questions.models import Question\n",
    "from apps.questions.models import Question\nfrom apps.roadmaps.models import Roadmap\n",
    label="review Roadmap import",
)
review_filter = """

def _selected_roadmap_question_filter(*, user, prefix="question__"):
    source_topic = f"{prefix}source_topic"
    roadmap = f"{source_topic}__section__roadmap"
    return (
        Q(**{f"{source_topic}__isnull": True})
        | Q(
            **{
                f"{roadmap}__source": Roadmap.Source.VIEWCOACH,
                f"{roadmap}__user_enrolments__user": user,
                f"{roadmap}__user_enrolments__is_focused": True,
            }
        )
        | Q(
            **{
                f"{roadmap}__source": Roadmap.Source.YOUTUBE,
                f"{roadmap}__youtube_playlist__user": user,
                f"{roadmap}__youtube_playlist__is_favourite": True,
            }
        )
        | Q(
            **{
                f"{roadmap}__source__in": [
                    Roadmap.Source.IBM,
                    Roadmap.Source.CUSTOM,
                ],
                f"{roadmap}__user_enrolments__user": user,
                f"{roadmap}__user_enrolments__is_focused": True,
            }
        )
    )


"""
changes["reviews"] = insert_before(
    changes["reviews"],
    "def sync_ready_review_states(*, user, now=None):\n",
    review_filter,
    label="review selected-roadmap helper",
)
changes["reviews"] = replace_once(
    changes["reviews"],
    """        ReviewState.objects.filter(\n            user=user,\n            question__owner=user,\n            question__status=Question.Status.READY_FOR_REVIEW,\n            due_at__lte=current_time,\n        )\n""",
    """        ReviewState.objects.filter(\n            user=user,\n            question__owner=user,\n            question__status=Question.Status.READY_FOR_REVIEW,\n            due_at__lte=current_time,\n        )\n        .filter(_selected_roadmap_question_filter(user=user))\n""",
    label="due review focus filter",
)
changes["reviews"] = replace_once(
    changes["reviews"],
    """        ReviewState.objects.filter(\n            user=user,\n            question__owner=user,\n            question__status=Question.Status.READY_FOR_REVIEW,\n            due_at__gt=current_time,\n        )\n""",
    """        ReviewState.objects.filter(\n            user=user,\n            question__owner=user,\n            question__status=Question.Status.READY_FOR_REVIEW,\n            due_at__gt=current_time,\n        )\n        .filter(_selected_roadmap_question_filter(user=user))\n""",
    label="upcoming review focus filter",
)
changes["reviews"] = replace_once(
    changes["reviews"],
    """    active_states = ReviewState.objects.filter(\n        user=user,\n        question__owner=user,\n        question__status=Question.Status.READY_FOR_REVIEW,\n    )\n""",
    """    active_states = (\n        ReviewState.objects.filter(\n            user=user,\n            question__owner=user,\n            question__status=Question.Status.READY_FOR_REVIEW,\n        )\n        .filter(_selected_roadmap_question_filter(user=user))\n        .distinct()\n    )\n""",
    label="dashboard review focus filter",
)
# Add distinct to due/upcoming query returns after select_related chains.
changes["reviews"] = changes["reviews"].replace(
    ")\n        .order_by(\"due_at\", \"pk\")\n    )\n",
    ")\n        .distinct()\n        .order_by(\"due_at\", \"pk\")\n    )\n",
    2,
)

# ---------------------------------------------------------------------------
# Dashboard: only focused/favourite roadmaps appear
# ---------------------------------------------------------------------------
changes["core_views"] = replace_once(
    changes["core_views"],
    "def _prioritised_learning_cards(groups, *, limit=2):\n",
    "def _prioritised_learning_cards(groups, *, limit=2, focused_only=False):\n",
    label="dashboard focused option",
)
changes["core_views"] = replace_once(
    changes["core_views"],
    """    cards = [item for group in groups for item in group[\"items\"]]\n""",
    """    cards = [item for group in groups for item in group[\"items\"]]\n    if focused_only:\n        cards = [\n            item\n            for item in cards\n            if item[\"enrolment\"] is not None and item[\"enrolment\"].is_focused\n        ]\n""",
    label="dashboard focused card filter",
)
changes["core_views"] = replace_once(
    changes["core_views"],
    "youtube_cards = youtube_roadmap_cards(user=request.user)\n",
    "youtube_cards = youtube_roadmap_cards(user=request.user, favourites_only=True)\n",
    label="dashboard favourite YouTube cards",
)
changes["core_views"] = replace_once(
    changes["core_views"],
    """            \"viewcoach_learning_cards\": _prioritised_learning_cards(viewcoach_groups),\n""",
    """            \"viewcoach_learning_cards\": _prioritised_learning_cards(\n                viewcoach_groups,\n                focused_only=True,\n            ),\n""",
    label="dashboard focused ViewCoach cards",
)

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
changes["roadmap_list"] = """{% extends \"base.html\" %}

{% block title %}ViewCoach Roadmaps | ViewCoach{% endblock %}
{% block body_class %}roadmap-source-page{% endblock %}

{% block content %}
<section class=\"source-page-shell\">
    <header class=\"source-page-header\">
        <div>
            <p class=\"source-page-kicker\">Curated curriculum</p>
            <h1>ViewCoach roadmaps</h1>
            <p>Browse every built-in roadmap, but keep only four in focus so ViewCoach can help you finish what you start.</p>
        </div>
        <div class=\"roadmap-selection-summary\">
            <strong>{{ focused_count }} / {{ focused_limit }}</strong>
            <span>focused roadmaps</span>
            <a class=\"button button-secondary\" href=\"{% url 'roadmaps:youtube_list' %}\">Open YouTube roadmaps</a>
        </div>
    </header>

    <nav class=\"source-switcher\" aria-label=\"Roadmap source\">
        <a class=\"is-active\" href=\"{% url 'roadmaps:list' %}\" aria-current=\"page\">
            <span class=\"source-switcher-icon is-viewcoach\" aria-hidden=\"true\">V</span>
            <span><strong>ViewCoach</strong><small>Built-in curriculum</small></span>
        </a>
        <a href=\"{% url 'roadmaps:youtube_list' %}\">
            <span class=\"source-switcher-icon is-youtube\" aria-hidden=\"true\">▶</span>
            <span><strong>YouTube</strong><small>Imported playlists</small></span>
        </a>
    </nav>

    {% for group in roadmap_groups %}
        <section class=\"roadmap-group source-roadmap-group\">
            <div class=\"roadmap-group-heading\">
                <div>
                    <p class=\"source-page-kicker\">{{ group.label }}</p>
                    <h2>
                        {% if group.kind == \"ROLE\" %}Prepare for a role
                        {% elif group.kind == \"SKILL\" %}Build a focused skill
                        {% else %}Turn knowledge into practice
                        {% endif %}
                    </h2>
                </div>
                <span>{{ group.items|length }} roadmap{{ group.items|length|pluralize }}</span>
            </div>

            <div class=\"source-roadmap-grid\">
                {% for item in group.items %}
                    <article class=\"source-roadmap-card {% if item.enrolment.is_focused %}is-selected-roadmap{% endif %}\">
                        <div class=\"source-roadmap-card-topline\">
                            <span class=\"source-badge is-viewcoach\">ViewCoach</span>
                            <span>{% if item.enrolment.is_focused %}Focused{% else %}{{ item.topic_count }} topics{% endif %}</span>
                        </div>
                        <h3><a href=\"{% url 'roadmaps:detail' item.roadmap.slug %}\">{{ item.roadmap.title }}</a></h3>
                        <p>{{ item.roadmap.description }}</p>
                        <div class=\"source-roadmap-progress-copy\">
                            <span>{% if item.enrolment %}{{ item.enrolment.get_status_display }}{% else %}Not started{% endif %}</span>
                            <strong>{{ item.percentage }}%</strong>
                        </div>
                        <div class=\"source-roadmap-progress\" role=\"progressbar\" aria-label=\"{{ item.roadmap.title }} progress\" aria-valuemin=\"0\" aria-valuemax=\"100\" aria-valuenow=\"{{ item.percentage }}\">
                            <span style=\"width: {{ item.percentage }}%\"></span>
                        </div>
                        <div class=\"roadmap-card-controls\">
                            <a class=\"source-roadmap-card-link\" href=\"{% url 'roadmaps:detail' item.roadmap.slug %}\">
                                {% if item.enrolment %}Continue roadmap{% else %}Explore roadmap{% endif %}
                                <span aria-hidden=\"true\">→</span>
                            </a>
                            <form method=\"post\" action=\"{% url 'roadmaps:focus' item.roadmap.slug %}\">
                                {% csrf_token %}
                                <input type=\"hidden\" name=\"focused\" value=\"{% if item.enrolment.is_focused %}false{% else %}true{% endif %}\">
                                <input type=\"hidden\" name=\"next\" value=\"{% url 'roadmaps:list' %}\">
                                <button class=\"roadmap-selection-button\" type=\"submit\">
                                    {% if item.enrolment.is_focused %}Remove focus{% else %}Add to focus{% endif %}
                                </button>
                            </form>
                        </div>
                    </article>
                {% endfor %}
            </div>
        </section>
    {% empty %}
        <div class=\"source-empty-state\">
            <span class=\"source-switcher-icon is-viewcoach\" aria-hidden=\"true\">V</span>
            <h2>No ViewCoach roadmaps are published yet</h2>
            <p>Run the roadmap seed command to create the built-in curriculum.</p>
        </div>
    {% endfor %}
</section>
{% endblock %}
"""

changes["roadmap_detail"] = replace_once(
    changes["roadmap_detail"],
    """        {% if user_roadmap %}\n            <strong>{{ user_roadmap.get_status_display }}</strong>\n        {% else %}\n            <form method=\"post\" action=\"{% url 'roadmaps:start' roadmap.slug %}\">\n                {% csrf_token %}\n                <button class=\"button\" type=\"submit\">Start this roadmap</button>\n            </form>\n        {% endif %}\n""",
    """        {% if user_roadmap %}\n            <strong>{{ user_roadmap.get_status_display }}</strong>\n        {% endif %}\n        <form method=\"post\" action=\"{% url 'roadmaps:focus' roadmap.slug %}\">\n            {% csrf_token %}\n            <input type=\"hidden\" name=\"focused\" value=\"{% if user_roadmap.is_focused %}false{% else %}true{% endif %}\">\n            <button class=\"button{% if user_roadmap.is_focused %} button-secondary{% endif %}\" type=\"submit\">\n                {% if user_roadmap.is_focused %}\n                    Remove from focus\n                {% else %}\n                    Add to focus ({{ focused_count }}/{{ focused_limit }})\n                {% endif %}\n            </button>\n        </form>\n""",
    label="roadmap detail focus control",
)

changes["youtube_list"] = """{% extends \"base.html\" %}

{% block title %}YouTube Roadmaps | ViewCoach{% endblock %}
{% block body_class %}roadmap-source-page youtube-library-page{% endblock %}

{% block content %}
<section class=\"source-page-shell\">
    <header class=\"source-page-header\">
        <div>
            <p class=\"source-page-kicker\">External learning</p>
            <h1>YouTube roadmaps</h1>
            <p>Save as many playlists as you need, organise them into groups, and favourite up to five for your dashboard and study planner.</p>
        </div>
        <div class=\"roadmap-selection-summary\">
            <strong>{{ favourite_count }} / {{ favourite_limit }}</strong>
            <span>favourite roadmaps</span>
            <a class=\"button\" href=\"{% url 'roadmaps:youtube_import' %}\">Import playlist</a>
        </div>
    </header>

    <nav class=\"source-switcher\" aria-label=\"Roadmap source\">
        <a href=\"{% url 'roadmaps:list' %}\">
            <span class=\"source-switcher-icon is-viewcoach\" aria-hidden=\"true\">V</span>
            <span><strong>ViewCoach</strong><small>Built-in curriculum</small></span>
        </a>
        <a class=\"is-active\" href=\"{% url 'roadmaps:youtube_list' %}\" aria-current=\"page\">
            <span class=\"source-switcher-icon is-youtube\" aria-hidden=\"true\">▶</span>
            <span><strong>YouTube</strong><small>Imported playlists</small></span>
        </a>
    </nav>

    <section class=\"youtube-group-creator\" aria-labelledby=\"youtube-group-creator-heading\">
        <div>
            <p class=\"source-page-kicker\">Organisation</p>
            <h2 id=\"youtube-group-creator-heading\">Create a playlist group</h2>
        </div>
        <form method=\"post\" action=\"{% url 'roadmaps:youtube_group_create' %}\">
            {% csrf_token %}
            {{ group_form.name }}
            <button class=\"button button-secondary\" type=\"submit\">Create group</button>
        </form>
    </section>

    {% if youtube_roadmaps %}
        {% for roadmap_group in youtube_groups %}
            <section class=\"source-roadmap-group youtube-group-section\" aria-labelledby=\"youtube-group-{{ forloop.counter }}\">
                <div class=\"roadmap-group-heading youtube-group-heading\">
                    <div>
                        <p class=\"source-page-kicker\">Playlist group</p>
                        <h2 id=\"youtube-group-{{ forloop.counter }}\">{{ roadmap_group.label }}</h2>
                    </div>
                    <div class=\"youtube-group-heading-actions\">
                        <span>{{ roadmap_group.items|length }} roadmap{{ roadmap_group.items|length|pluralize }}</span>
                        {% if roadmap_group.group %}
                            <details>
                                <summary>Manage</summary>
                                <div class=\"youtube-group-management\">
                                    <form method=\"post\" action=\"{% url 'roadmaps:youtube_group_rename' roadmap_group.group.pk %}\">
                                        {% csrf_token %}
                                        <input type=\"text\" name=\"name\" maxlength=\"80\" value=\"{{ roadmap_group.group.name }}\" required>
                                        <button class=\"button button-secondary\" type=\"submit\">Rename</button>
                                    </form>
                                    <form method=\"post\" action=\"{% url 'roadmaps:youtube_group_delete' roadmap_group.group.pk %}\">
                                        {% csrf_token %}
                                        <button class=\"roadmap-selection-button\" type=\"submit\">Delete group</button>
                                    </form>
                                </div>
                            </details>
                        {% endif %}
                    </div>
                </div>

                {% if roadmap_group.items %}
                    <div class=\"source-roadmap-grid youtube-roadmap-grid\">
                        {% for item in roadmap_group.items %}
                            <article class=\"source-roadmap-card youtube-roadmap-card {% if item.youtube_source.is_favourite %}is-selected-roadmap{% endif %}\">
                                {% if item.youtube_source.thumbnail_url %}
                                    <a class=\"youtube-roadmap-thumbnail\" href=\"{% url 'roadmaps:youtube_detail' item.roadmap.slug %}\" aria-label=\"Open {{ item.roadmap.title }}\">
                                        <img src=\"{{ item.youtube_source.thumbnail_url }}\" alt=\"\">
                                        <span aria-hidden=\"true\">▶</span>
                                    </a>
                                {% endif %}
                                <div class=\"source-roadmap-card-body\">
                                    <div class=\"source-roadmap-card-topline\">
                                        <span class=\"source-badge is-youtube\">YouTube</span>
                                        <span>{% if item.youtube_source.is_favourite %}★ Favourite{% else %}{{ item.youtube_source.total_duration_display }}{% endif %}</span>
                                    </div>
                                    <h3><a href=\"{% url 'roadmaps:youtube_detail' item.roadmap.slug %}\">{{ item.roadmap.title }}</a></h3>
                                    <p>
                                        {% if item.youtube_source.channel_title %}{{ item.youtube_source.channel_title }} · {% endif %}
                                        {{ item.youtube_source.available_video_count }} available video{{ item.youtube_source.available_video_count|pluralize }}
                                    </p>
                                    <div class=\"source-roadmap-progress-copy\">
                                        <span>{% if item.enrolment %}{{ item.enrolment.get_status_display }}{% else %}Not started{% endif %}</span>
                                        <strong>{{ item.percentage }}%</strong>
                                    </div>
                                    <div class=\"source-roadmap-progress\" role=\"progressbar\" aria-label=\"{{ item.roadmap.title }} progress\" aria-valuemin=\"0\" aria-valuemax=\"100\" aria-valuenow=\"{{ item.percentage }}\">
                                        <span style=\"width: {{ item.percentage }}%\"></span>
                                    </div>
                                    <div class=\"youtube-roadmap-controls\">
                                        <form method=\"post\" action=\"{% url 'roadmaps:youtube_favourite' item.roadmap.slug %}\">
                                            {% csrf_token %}
                                            <input type=\"hidden\" name=\"favourite\" value=\"{% if item.youtube_source.is_favourite %}false{% else %}true{% endif %}\">
                                            <button class=\"roadmap-selection-button\" type=\"submit\">
                                                {% if item.youtube_source.is_favourite %}Unfavourite{% else %}Favourite{% endif %}
                                            </button>
                                        </form>
                                        <form class=\"youtube-roadmap-move-form\" method=\"post\" action=\"{% url 'roadmaps:youtube_move' item.roadmap.slug %}\">
                                            {% csrf_token %}
                                            <label class=\"sr-only\" for=\"group-{{ item.youtube_source.pk }}\">Move {{ item.roadmap.title }}</label>
                                            <select id=\"group-{{ item.youtube_source.pk }}\" name=\"group_id\">
                                                <option value=\"\"{% if not item.youtube_source.group_id %} selected{% endif %}>Ungrouped</option>
                                                {% for choice in group_choices %}
                                                    <option value=\"{{ choice.pk }}\"{% if item.youtube_source.group_id == choice.pk %} selected{% endif %}>{{ choice.name }}</option>
                                                {% endfor %}
                                            </select>
                                            <button class=\"button button-secondary\" type=\"submit\">Move</button>
                                        </form>
                                    </div>
                                    <a class=\"source-roadmap-card-link\" href=\"{% url 'roadmaps:youtube_detail' item.roadmap.slug %}\">
                                        {% if item.enrolment %}Continue playlist{% else %}Open playlist roadmap{% endif %}
                                        <span aria-hidden=\"true\">→</span>
                                    </a>
                                </div>
                            </article>
                        {% endfor %}
                    </div>
                {% else %}
                    <div class=\"source-empty-state compact\">
                        <p>This group is empty. Move a playlist here using its group selector.</p>
                    </div>
                {% endif %}
            </section>
        {% empty %}
            <div class=\"source-empty-state\">
                <p>Your imported playlists are currently ungrouped.</p>
            </div>
        {% endfor %}
    {% else %}
        <div class=\"source-empty-state youtube-empty-state\">
            <span class=\"source-switcher-icon is-youtube\" aria-hidden=\"true\">▶</span>
            <h2>No YouTube roadmaps yet</h2>
            <p>Import a playlist and ViewCoach will turn its available videos into a private, ordered learning path.</p>
            <a class=\"button\" href=\"{% url 'roadmaps:youtube_import' %}\">Import your first playlist</a>
        </div>
    {% endif %}
</section>
{% endblock %}
"""

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
changes["css"] = append_once(
    changes["css"],
    """

/* Patch 3A: focused/favourite roadmap controls and YouTube groups */
.roadmap-selection-summary {
    display: grid;
    gap: 0.25rem;
    justify-items: end;
    min-width: 12rem;
}

.roadmap-selection-summary strong {
    font-size: 1.5rem;
}

.roadmap-selection-summary span {
    color: var(--vc-muted);
    font-size: 0.78rem;
}

.is-selected-roadmap {
    border-color: #9eb5c3;
    box-shadow: 0 0 0 2px rgba(77, 111, 130, 0.12);
}

.roadmap-card-controls,
.youtube-roadmap-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-top: 1rem;
}

.roadmap-selection-button {
    padding: 0.55rem 0.75rem;
    border: 1px solid var(--vc-border-strong);
    background: transparent;
    color: var(--vc-ink);
    cursor: pointer;
    font: inherit;
    font-size: 0.78rem;
    font-weight: 750;
}

.roadmap-selection-button:hover,
.roadmap-selection-button:focus-visible {
    border-color: var(--vc-ink);
    outline: none;
}

.youtube-group-creator {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 1.5rem;
    margin: 2rem 0 0;
    padding: 1.25rem;
    border: 1px solid var(--vc-border);
    background: #fff;
}

.youtube-group-creator h2 {
    margin: 0.25rem 0 0;
}

.youtube-group-creator form,
.youtube-group-management form,
.youtube-roadmap-move-form {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    align-items: center;
}

.youtube-group-creator input,
.youtube-group-management input,
.youtube-roadmap-move-form select {
    min-height: 2.5rem;
    padding: 0.55rem 0.7rem;
    border: 1px solid var(--vc-border-strong);
    background: #fff;
    color: var(--vc-ink);
    font: inherit;
}

.youtube-group-heading-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.youtube-group-heading-actions summary {
    cursor: pointer;
    font-size: 0.8rem;
    font-weight: 750;
}

.youtube-group-management {
    display: grid;
    gap: 0.75rem;
    min-width: min(28rem, 80vw);
    margin-top: 0.75rem;
    padding: 0.9rem;
    border: 1px solid var(--vc-border);
    background: #fff;
}

.source-empty-state.compact {
    padding: 1.25rem;
}

@media (max-width: 48rem) {
    .roadmap-selection-summary {
        justify-items: start;
    }

    .youtube-group-creator,
    .youtube-group-heading-actions,
    .roadmap-card-controls,
    .youtube-roadmap-controls {
        align-items: stretch;
        flex-direction: column;
    }

    .youtube-group-creator form,
    .youtube-group-management form,
    .youtube-roadmap-move-form {
        align-items: stretch;
        flex-direction: column;
    }
}
""",
)

# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------
migration_path = ROOT / "apps/roadmaps/migrations/0005_roadmap_focus_and_youtube_groups.py"
migration_content = """from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def preserve_current_learning_choices(apps, schema_editor):
    UserRoadmap = apps.get_model("roadmaps", "UserRoadmap")
    YouTubePlaylistRoadmap = apps.get_model("roadmaps", "YouTubePlaylistRoadmap")

    user_ids = (
        UserRoadmap.objects.filter(
            status="IN_PROGRESS",
            roadmap__source="VIEWCOACH",
        )
        .values_list("user_id", flat=True)
        .distinct()
    )
    for user_id in user_ids:
        focused_ids = list(
            UserRoadmap.objects.filter(
                user_id=user_id,
                status="IN_PROGRESS",
                roadmap__source="VIEWCOACH",
            )
            .order_by("started_at", "created_at", "pk")
            .values_list("pk", flat=True)[:4]
        )
        UserRoadmap.objects.filter(pk__in=focused_ids).update(is_focused=True)

    youtube_user_ids = (
        YouTubePlaylistRoadmap.objects.values_list("user_id", flat=True).distinct()
    )
    for user_id in youtube_user_ids:
        favourite_ids = list(
            YouTubePlaylistRoadmap.objects.filter(user_id=user_id)
            .order_by("-updated_at", "-pk")
            .values_list("pk", flat=True)[:5]
        )
        YouTubePlaylistRoadmap.objects.filter(pk__in=favourite_ids).update(
            is_favourite=True
        )


class Migration(migrations.Migration):
    dependencies = [
        ("roadmaps", "0004_roadmap_source"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="YouTubeRoadmapGroup",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=80)),
                ("position", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="youtube_roadmap_groups",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["position", "name", "pk"],
            },
        ),
        migrations.AddField(
            model_name="userroadmap",
            name="is_focused",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="youtubeplaylistroadmap",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="roadmaps",
                to="roadmaps.youtuberoadmapgroup",
            ),
        ),
        migrations.AddField(
            model_name="youtubeplaylistroadmap",
            name="is_favourite",
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name="youtuberoadmapgroup",
            constraint=models.UniqueConstraint(
                fields=("user", "name"),
                name="unique_user_youtube_group_name",
            ),
        ),
        migrations.AddIndex(
            model_name="youtuberoadmapgroup",
            index=models.Index(
                fields=["user", "position"],
                name="yt_group_user_position_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userroadmap",
            index=models.Index(
                fields=["user", "is_focused"],
                name="user_roadmap_focus_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="youtubeplaylistroadmap",
            index=models.Index(
                fields=["user", "is_favourite"],
                name="yt_playlist_user_fav_idx",
            ),
        ),
        migrations.RunPython(
            preserve_current_learning_choices,
            migrations.RunPython.noop,
        ),
    ]
"""
if migration_path.exists() and migration_path.read_text() != migration_content:
    raise SystemExit(f"Refusing to overwrite existing migration: {migration_path}")

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
test_path = ROOT / "apps/roadmaps/tests/test_roadmap_selection_and_groups.py"
test_content = """import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.roadmaps.models import (
    Roadmap,
    UserRoadmap,
    YouTubeRoadmapGroup,
)
from apps.roadmaps.services import (
    MAX_FAVOURITE_YOUTUBE_ROADMAPS,
    MAX_FOCUSED_VIEWCOACH_ROADMAPS,
    RoadmapSelectionLimitError,
    set_viewcoach_roadmap_focus,
    set_youtube_roadmap_favourite,
)
from apps.roadmaps.youtube_client import PlaylistPreview, PlaylistVideoPreview
from apps.roadmaps.youtube_services import create_youtube_roadmap

pytestmark = pytest.mark.django_db


def create_user(email="tee@example.com"):
    return get_user_model().objects.create_user(
        email=email,
        password="safe-password",
    )


def create_viewcoach_roadmap(position):
    return Roadmap.objects.create(
        title=f"Roadmap {position}",
        slug=f"roadmap-{position}",
        description="",
        kind=Roadmap.Kind.SKILL,
        source=Roadmap.Source.VIEWCOACH,
        position=position,
        is_system=True,
        is_published=True,
    )


def preview(number):
    return PlaylistPreview(
        playlist_id=f"PL{number:014d}",
        source_url=f"https://www.youtube.com/playlist?list=PL{number:014d}",
        title=f"Course {number}",
        description="",
        channel_title="Example Channel",
        thumbnail_url="",
        videos=(
            PlaylistVideoPreview(
                playlist_item_id=f"item-{number}",
                video_id=f"video-{number}",
                title="Lesson",
                channel_title="Example Channel",
                thumbnail_url="",
                duration_seconds=600,
                position=0,
                available=True,
                embeddable=True,
                made_for_kids=False,
            ),
        ),
    )


def test_only_four_viewcoach_roadmaps_can_be_focused():
    user = create_user()
    roadmaps = [create_viewcoach_roadmap(index) for index in range(5)]

    for roadmap in roadmaps[:MAX_FOCUSED_VIEWCOACH_ROADMAPS]:
        set_viewcoach_roadmap_focus(user=user, roadmap=roadmap, focused=True)

    with pytest.raises(RoadmapSelectionLimitError):
        set_viewcoach_roadmap_focus(user=user, roadmap=roadmaps[-1], focused=True)

    assert UserRoadmap.objects.filter(user=user, is_focused=True).count() == 4


def test_unfocusing_preserves_enrolment_and_progress_state():
    user = create_user()
    roadmap = create_viewcoach_roadmap(1)
    enrolment = set_viewcoach_roadmap_focus(user=user, roadmap=roadmap, focused=True)

    set_viewcoach_roadmap_focus(user=user, roadmap=roadmap, focused=False)

    enrolment.refresh_from_db()
    assert enrolment.status == UserRoadmap.Status.IN_PROGRESS
    assert enrolment.is_focused is False


def test_only_five_youtube_roadmaps_can_be_favourited():
    user = create_user()
    sources = [create_youtube_roadmap(user=user, preview=preview(index))[0] for index in range(6)]

    assert sum(source.is_favourite for source in sources) == MAX_FAVOURITE_YOUTUBE_ROADMAPS
    with pytest.raises(RoadmapSelectionLimitError):
        set_youtube_roadmap_favourite(
            user=user,
            source=sources[-1],
            favourite=True,
        )


def test_deleting_group_moves_playlist_to_ungrouped(client):
    user = create_user()
    source, _ = create_youtube_roadmap(user=user, preview=preview(1))
    group = YouTubeRoadmapGroup.objects.create(user=user, name="Backend")
    source.group = group
    source.save(update_fields=["group", "updated_at"])
    client.force_login(user)

    response = client.post(
        reverse("roadmaps:youtube_group_delete", kwargs={"group_id": group.pk})
    )

    assert response.status_code == 302
    source.refresh_from_db()
    assert source.group is None


def test_user_cannot_move_playlist_into_another_users_group(client):
    user = create_user()
    other = create_user("other@example.com")
    source, _ = create_youtube_roadmap(user=user, preview=preview(1))
    other_group = YouTubeRoadmapGroup.objects.create(user=other, name="Private")
    client.force_login(user)

    response = client.post(
        reverse("roadmaps:youtube_move", kwargs={"slug": source.roadmap.slug}),
        {"group_id": other_group.pk},
    )

    assert response.status_code == 404
"""
if test_path.exists() and test_path.read_text() != test_content:
    raise SystemExit(f"Refusing to overwrite existing test file: {test_path}")

# Validate all replacement targets before writing anything.
for key, path in paths.items():
    if not changes[key].strip():
        raise SystemExit(f"Generated empty content for {path}")

for key, path in paths.items():
    path.write_text(changes[key])
migration_path.write_text(migration_content)
test_path.write_text(test_content)

print("Applied ViewCoach Patch 3A.")
print("Next: python manage.py migrate")
print("Then run the verification commands from the patch notes.")
