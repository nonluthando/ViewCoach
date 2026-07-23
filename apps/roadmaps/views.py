from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Roadmap, RoadmapTopic, UserRoadmap, UserTopicProgress
from .services import grouped_roadmap_cards, roadmap_progress, sync_user_roadmap


def _accessible_roadmap(user, slug):
    return get_object_or_404(
        Roadmap.objects.prefetch_related("sections__topics").filter(
            Q(is_system=True) | Q(created_by=user)
        ),
        slug=slug,
        is_published=True,
    )


@login_required
def roadmap_list(request):
    return render(
        request,
        "roadmaps/roadmap_list.html",
        {"roadmap_groups": grouped_roadmap_cards(user=request.user)},
    )


@login_required
def roadmap_detail(request, slug):
    roadmap = _accessible_roadmap(request.user, slug)
    progress_by_topic = {
        progress.topic_id: progress
        for progress in UserTopicProgress.objects.filter(
            user=request.user,
            topic__section__roadmap=roadmap,
        )
    }

    sections = list(roadmap.sections.all())
    for section in sections:
        section.topic_items = list(section.topics.all())
        for topic in section.topic_items:
            topic.current_progress = progress_by_topic.get(topic.pk)
            topic.current_status = (
                topic.current_progress.status
                if topic.current_progress
                else UserTopicProgress.Status.NOT_STARTED
            )

    return render(
        request,
        "roadmaps/roadmap_detail.html",
        {
            "roadmap": roadmap,
            "sections": sections,
            "user_roadmap": UserRoadmap.objects.filter(
                user=request.user,
                roadmap=roadmap,
            ).first(),
            "progress": roadmap_progress(user=request.user, roadmap=roadmap),
        },
    )


@login_required
@require_POST
def start_roadmap(request, slug):
    roadmap = _accessible_roadmap(request.user, slug)
    user_roadmap, created = UserRoadmap.objects.get_or_create(
        user=request.user,
        roadmap=roadmap,
        defaults={
            "status": UserRoadmap.Status.IN_PROGRESS,
            "started_at": timezone.now(),
        },
    )
    if created or not user_roadmap.started_at:
        user_roadmap.status = UserRoadmap.Status.IN_PROGRESS
        user_roadmap.started_at = user_roadmap.started_at or timezone.now()
        user_roadmap.save(update_fields=["status", "started_at", "updated_at"])
    sync_user_roadmap(user=request.user, roadmap=roadmap)

    messages.success(request, f"{roadmap.title} is now one of your active roadmaps.")
    return redirect("roadmaps:detail", slug=roadmap.slug)


@login_required
@require_POST
def update_topic_status(request, slug, topic_id):
    roadmap = _accessible_roadmap(request.user, slug)
    topic = get_object_or_404(
        RoadmapTopic.objects.select_related(
            "section",
            "section__roadmap",
        ),
        pk=topic_id,
        section__roadmap=roadmap,
    )
    status = request.POST.get("status", "")
    valid_statuses = {value for value, _ in UserTopicProgress.Status.choices}
    if status not in valid_statuses:
        messages.error(request, "Choose a valid topic status.")
        return redirect("roadmaps:detail", slug=roadmap.slug)

    now = timezone.now()
    progress, _ = UserTopicProgress.objects.get_or_create(
        user=request.user,
        topic=topic,
    )
    progress.status = status
    if status == UserTopicProgress.Status.NOT_STARTED:
        progress.started_at = None
        progress.completed_at = None
    elif status == UserTopicProgress.Status.IN_PROGRESS:
        progress.started_at = progress.started_at or now
        progress.completed_at = None
    else:
        progress.started_at = progress.started_at or now
        progress.completed_at = now
    progress.save()
    sync_user_roadmap(user=request.user, roadmap=roadmap)

    messages.success(request, f"Updated {topic.title} to {progress.get_status_display()}.")
    detail_url = reverse("roadmaps:detail", kwargs={"slug": roadmap.slug})
    return redirect(f"{detail_url}#topic-{topic.pk}")
