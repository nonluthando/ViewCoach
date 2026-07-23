from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import TopicNotesForm, TopicResourceForm
from .models import (
    Roadmap,
    RoadmapTopic,
    UserRoadmap,
    UserTopicProgress,
    UserTopicResource,
)
from .services import grouped_roadmap_cards, roadmap_progress, sync_user_roadmap


def _accessible_roadmap(user, slug, *, with_topics=False):
    roadmaps = Roadmap.objects.filter(Q(is_system=True) | Q(created_by=user))
    if with_topics:
        roadmaps = roadmaps.prefetch_related("sections__topics")

    return get_object_or_404(
        roadmaps,
        slug=slug,
        is_published=True,
    )


def _accessible_topic(user, slug, topic_id):
    roadmap = _accessible_roadmap(user, slug)
    topic = get_object_or_404(
        RoadmapTopic.objects.select_related(
            "section",
            "section__roadmap",
        ),
        pk=topic_id,
        section__roadmap=roadmap,
    )
    return roadmap, topic


def _topic_navigation(roadmap, current_topic):
    topics = list(
        RoadmapTopic.objects.filter(section__roadmap=roadmap)
        .select_related("section")
        .order_by(
            "section__position",
            "section__title",
            "position",
            "title",
            "pk",
        )
    )
    current_index = next(
        index for index, topic in enumerate(topics) if topic.pk == current_topic.pk
    )
    previous_topic = topics[current_index - 1] if current_index > 0 else None
    next_topic = topics[current_index + 1] if current_index + 1 < len(topics) else None
    return {
        "previous_topic": previous_topic,
        "next_topic": next_topic,
        "topic_number": current_index + 1,
        "topic_count": len(topics),
    }


def _redirect_after_status_update(request, roadmap, topic):
    if request.POST.get("return_to") == "topic":
        return redirect(
            "roadmaps:topic_detail",
            slug=roadmap.slug,
            topic_id=topic.pk,
        )

    detail_url = reverse("roadmaps:detail", kwargs={"slug": roadmap.slug})
    return redirect(f"{detail_url}#topic-{topic.pk}")


@login_required
def roadmap_list(request):
    return render(
        request,
        "roadmaps/roadmap_list.html",
        {"roadmap_groups": grouped_roadmap_cards(user=request.user)},
    )


@login_required
def roadmap_detail(request, slug):
    roadmap = _accessible_roadmap(request.user, slug, with_topics=True)
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
def topic_detail(request, slug, topic_id):
    roadmap, topic = _accessible_topic(request.user, slug, topic_id)
    progress = UserTopicProgress.objects.filter(
        user=request.user,
        topic=topic,
    ).first()
    navigation = _topic_navigation(roadmap, topic)

    return render(
        request,
        "roadmaps/topic_detail.html",
        {
            "roadmap": roadmap,
            "topic": topic,
            "progress": progress,
            "current_status": (
                progress.status
                if progress
                else UserTopicProgress.Status.NOT_STARTED
            ),
            "notes_form": TopicNotesForm(instance=progress),
            "resource_form": TopicResourceForm(),
            "resources": UserTopicResource.objects.filter(
                user=request.user,
                topic=topic,
            ),
            **navigation,
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
    roadmap, topic = _accessible_topic(request.user, slug, topic_id)
    status = request.POST.get("status", "")
    valid_statuses = {value for value, _ in UserTopicProgress.Status.choices}
    if status not in valid_statuses:
        messages.error(request, "Choose a valid topic status.")
        return _redirect_after_status_update(request, roadmap, topic)

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
    return _redirect_after_status_update(request, roadmap, topic)


@login_required
@require_POST
def save_topic_notes(request, slug, topic_id):
    _, topic = _accessible_topic(request.user, slug, topic_id)
    progress, _ = UserTopicProgress.objects.get_or_create(
        user=request.user,
        topic=topic,
    )
    form = TopicNotesForm(request.POST, instance=progress)
    if form.is_valid():
        form.save()
        messages.success(request, "Topic notes saved.")
    else:
        messages.error(request, "Your notes could not be saved.")

    return redirect(
        "roadmaps:topic_detail",
        slug=slug,
        topic_id=topic.pk,
    )


@login_required
@require_POST
def add_topic_resource(request, slug, topic_id):
    _, topic = _accessible_topic(request.user, slug, topic_id)
    form = TopicResourceForm(request.POST)
    if form.is_valid():
        _, created = UserTopicResource.objects.get_or_create(
            user=request.user,
            topic=topic,
            url=form.cleaned_data["url"],
            defaults={"title": form.cleaned_data["title"]},
        )
        if created:
            messages.success(request, "Learning resource added.")
        else:
            messages.info(request, "That resource is already saved for this topic.")
    else:
        messages.error(request, "Add a title and a valid resource URL.")

    return redirect(
        "roadmaps:topic_detail",
        slug=slug,
        topic_id=topic.pk,
    )


@login_required
@require_POST
def delete_topic_resource(request, slug, topic_id, resource_id):
    _, topic = _accessible_topic(request.user, slug, topic_id)
    resource = get_object_or_404(
        UserTopicResource,
        pk=resource_id,
        user=request.user,
        topic=topic,
    )
    resource.delete()
    messages.success(request, "Learning resource removed.")
    return redirect(
        "roadmaps:topic_detail",
        slug=slug,
        topic_id=topic.pk,
    )
