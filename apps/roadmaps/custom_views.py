from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from .custom_forms import (
    CustomRoadmapForm,
    CustomSectionForm,
    CustomTopicForm,
)
from .custom_services import (
    create_custom_roadmap,
    create_custom_section,
    create_custom_topic,
    custom_roadmap_cards,
    delete_custom_section,
    delete_custom_topic,
    move_custom_section,
    move_custom_topic,
    set_custom_roadmap_focus,
)
from .models import Roadmap, RoadmapSection, RoadmapTopic


def _owned_custom_roadmap(user, slug, *, with_outline=False):
    roadmaps = Roadmap.objects.filter(
        created_by=user,
        source=Roadmap.Source.CUSTOM,
        external_course__isnull=True,
        is_system=False,
        is_published=True,
    )
    if with_outline:
        roadmaps = roadmaps.prefetch_related("sections__topics")
    return get_object_or_404(roadmaps, slug=slug)


def _owned_custom_section(user, slug, section_id):
    roadmap = _owned_custom_roadmap(user, slug)
    section = get_object_or_404(
        RoadmapSection.objects.select_related("roadmap"),
        pk=section_id,
        roadmap=roadmap,
    )
    return roadmap, section


def _owned_custom_topic(user, slug, topic_id):
    roadmap = _owned_custom_roadmap(user, slug)
    topic = get_object_or_404(
        RoadmapTopic.objects.select_related(
            "section",
            "section__roadmap",
        ),
        pk=topic_id,
        section__roadmap=roadmap,
    )
    return roadmap, topic.section, topic


def _form_context(
    *,
    form,
    title,
    intro,
    submit_label,
    cancel_url,
    eyebrow="My roadmaps",
):
    return {
        "form": form,
        "form_title": title,
        "form_intro": intro,
        "submit_label": submit_label,
        "cancel_url": cancel_url,
        "eyebrow": eyebrow,
    }


@login_required
def custom_roadmap_list(request):
    return render(
        request,
        "roadmaps/custom/custom_roadmap_list.html",
        {
            "custom_roadmaps": custom_roadmap_cards(user=request.user),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def create_custom_roadmap_view(request):
    form = CustomRoadmapForm(
        request.POST or None,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        roadmap = create_custom_roadmap(
            user=request.user,
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            kind=form.cleaned_data["kind"],
        )
        messages.success(
            request,
            "Roadmap created. Add modules and topics to shape the path.",
        )
        return redirect(
            "roadmaps:custom_manage",
            slug=roadmap.slug,
        )

    return render(
        request,
        "roadmaps/custom/custom_form.html",
        _form_context(
            form=form,
            title="Create a roadmap",
            intro=(
                "Start with the outcome you want. You can add and reorder "
                "modules and topics after saving."
            ),
            submit_label="Create roadmap",
            cancel_url=reverse("roadmaps:custom_list"),
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit_custom_roadmap(request, slug):
    roadmap = _owned_custom_roadmap(request.user, slug)
    form = CustomRoadmapForm(
        request.POST or None,
        instance=roadmap,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Roadmap details updated.")
        return redirect(
            "roadmaps:custom_manage",
            slug=roadmap.slug,
        )

    return render(
        request,
        "roadmaps/custom/custom_form.html",
        _form_context(
            form=form,
            title="Edit roadmap details",
            intro=(
                "Changing the title does not change the roadmap URL, "
                "so saved links remain stable."
            ),
            submit_label="Save changes",
            cancel_url=reverse(
                "roadmaps:custom_manage",
                kwargs={"slug": roadmap.slug},
            ),
        ),
    )


@login_required
def manage_custom_roadmap(request, slug):
    roadmap = _owned_custom_roadmap(
        request.user,
        slug,
        with_outline=True,
    )
    sections = list(roadmap.sections.all())
    for section in sections:
        section.topic_items = list(section.topics.all())

    return render(
        request,
        "roadmaps/custom/custom_manage.html",
        {
            "roadmap": roadmap,
            "sections": sections,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def create_custom_section_view(request, slug):
    roadmap = _owned_custom_roadmap(request.user, slug)
    form = CustomSectionForm(
        request.POST or None,
        roadmap=roadmap,
    )
    if request.method == "POST" and form.is_valid():
        create_custom_section(
            roadmap=roadmap,
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
        )
        messages.success(request, "Module added.")
        return redirect(
            "roadmaps:custom_manage",
            slug=roadmap.slug,
        )

    return render(
        request,
        "roadmaps/custom/custom_form.html",
        _form_context(
            form=form,
            title="Add a module",
            intro=(
                "Modules group related topics into a clear learning sequence."
            ),
            submit_label="Add module",
            cancel_url=reverse(
                "roadmaps:custom_manage",
                kwargs={"slug": roadmap.slug},
            ),
            eyebrow=roadmap.title,
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit_custom_section(request, slug, section_id):
    roadmap, section = _owned_custom_section(
        request.user,
        slug,
        section_id,
    )
    form = CustomSectionForm(
        request.POST or None,
        instance=section,
        roadmap=roadmap,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Module updated.")
        return redirect(
            "roadmaps:custom_manage",
            slug=roadmap.slug,
        )

    return render(
        request,
        "roadmaps/custom/custom_form.html",
        _form_context(
            form=form,
            title="Edit module",
            intro="Update the module name or its purpose.",
            submit_label="Save module",
            cancel_url=reverse(
                "roadmaps:custom_manage",
                kwargs={"slug": roadmap.slug},
            ),
            eyebrow=roadmap.title,
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def create_custom_topic_view(request, slug, section_id):
    roadmap, section = _owned_custom_section(
        request.user,
        slug,
        section_id,
    )
    form = CustomTopicForm(
        request.POST or None,
        section=section,
    )
    if request.method == "POST" and form.is_valid():
        create_custom_topic(
            section=section,
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            external_url=form.cleaned_data["external_url"],
            estimated_minutes=form.cleaned_data["estimated_minutes"],
        )
        messages.success(request, "Topic added.")
        return redirect(
            "roadmaps:custom_manage",
            slug=roadmap.slug,
        )

    return render(
        request,
        "roadmaps/custom/custom_form.html",
        _form_context(
            form=form,
            title="Add a topic",
            intro=(
                f"Add the next piece of work inside {section.title}."
            ),
            submit_label="Add topic",
            cancel_url=reverse(
                "roadmaps:custom_manage",
                kwargs={"slug": roadmap.slug},
            ),
            eyebrow=roadmap.title,
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit_custom_topic(request, slug, topic_id):
    roadmap, section, topic = _owned_custom_topic(
        request.user,
        slug,
        topic_id,
    )
    form = CustomTopicForm(
        request.POST or None,
        instance=topic,
        section=section,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Topic updated.")
        return redirect(
            "roadmaps:custom_manage",
            slug=roadmap.slug,
        )

    return render(
        request,
        "roadmaps/custom/custom_form.html",
        _form_context(
            form=form,
            title="Edit topic",
            intro=(
                "Update the learning outcome, resource link or time estimate."
            ),
            submit_label="Save topic",
            cancel_url=reverse(
                "roadmaps:custom_manage",
                kwargs={"slug": roadmap.slug},
            ),
            eyebrow=roadmap.title,
        ),
    )


@login_required
@require_POST
def move_custom_section_view(request, slug, section_id):
    roadmap, section = _owned_custom_section(
        request.user,
        slug,
        section_id,
    )
    direction = request.POST.get("direction", "")
    try:
        moved = move_custom_section(
            roadmap=roadmap,
            section=section,
            direction=direction,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        if not moved:
            messages.info(
                request,
                "That module is already at the edge of the roadmap.",
            )
    return redirect("roadmaps:custom_manage", slug=roadmap.slug)


@login_required
@require_POST
def move_custom_topic_view(request, slug, topic_id):
    roadmap, section, topic = _owned_custom_topic(
        request.user,
        slug,
        topic_id,
    )
    direction = request.POST.get("direction", "")
    try:
        moved = move_custom_topic(
            section=section,
            topic=topic,
            direction=direction,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        if not moved:
            messages.info(
                request,
                "That topic is already at the edge of the module.",
            )
    return redirect("roadmaps:custom_manage", slug=roadmap.slug)


@login_required
@require_http_methods(["GET", "POST"])
def delete_custom_roadmap_view(request, slug):
    roadmap = _owned_custom_roadmap(
        request.user,
        slug,
        with_outline=True,
    )
    topic_count = sum(
        len(section.topics.all())
        for section in roadmap.sections.all()
    )
    if request.method == "POST":
        title = roadmap.title
        roadmap.delete()
        messages.success(request, f"Deleted {title}.")
        return redirect("roadmaps:custom_list")

    return render(
        request,
        "roadmaps/custom/custom_delete_confirm.html",
        {
            "eyebrow": "Delete roadmap",
            "object_name": roadmap.title,
            "warning": (
                f"This removes {topic_count} topic"
                f"{'s' if topic_count != 1 else ''}, their progress, notes, "
                "resources and evidence links. Generated question cards remain "
                "in your question library but lose their roadmap source link."
            ),
            "cancel_url": reverse(
                "roadmaps:custom_manage",
                kwargs={"slug": roadmap.slug},
            ),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def delete_custom_section_view(request, slug, section_id):
    roadmap, section = _owned_custom_section(
        request.user,
        slug,
        section_id,
    )
    topic_count = section.topics.count()
    if request.method == "POST":
        title = section.title
        delete_custom_section(
            user=request.user,
            section=section,
        )
        messages.success(request, f"Deleted {title}.")
        return redirect(
            "roadmaps:custom_manage",
            slug=roadmap.slug,
        )

    return render(
        request,
        "roadmaps/custom/custom_delete_confirm.html",
        {
            "eyebrow": "Delete module",
            "object_name": section.title,
            "warning": (
                f"This removes {topic_count} topic"
                f"{'s' if topic_count != 1 else ''} and their attached "
                "progress, notes, resources and evidence links."
            ),
            "cancel_url": reverse(
                "roadmaps:custom_manage",
                kwargs={"slug": roadmap.slug},
            ),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def delete_custom_topic_view(request, slug, topic_id):
    roadmap, _section, topic = _owned_custom_topic(
        request.user,
        slug,
        topic_id,
    )
    if request.method == "POST":
        title = topic.title
        delete_custom_topic(
            user=request.user,
            topic=topic,
        )
        messages.success(request, f"Deleted {title}.")
        return redirect(
            "roadmaps:custom_manage",
            slug=roadmap.slug,
        )

    return render(
        request,
        "roadmaps/custom/custom_delete_confirm.html",
        {
            "eyebrow": "Delete topic",
            "object_name": topic.title,
            "warning": (
                "This removes its progress, notes, resources and evidence "
                "links. Generated question cards remain in your question "
                "library but lose their roadmap source link."
            ),
            "cancel_url": reverse(
                "roadmaps:custom_manage",
                kwargs={"slug": roadmap.slug},
            ),
        },
    )


@login_required
@require_POST
def toggle_custom_roadmap_focus(request, slug):
    roadmap = _owned_custom_roadmap(request.user, slug)
    focused = request.POST.get("focused") == "true"
    try:
        enrolment = set_custom_roadmap_focus(
            user=request.user,
            roadmap=roadmap,
            focused=focused,
        )
    except ValueError as exc:
        messages.warning(request, str(exc))
    else:
        if enrolment.is_focused:
            messages.success(
                request,
                f"{roadmap.title} can now appear in daily plans.",
            )
        else:
            messages.info(
                request,
                f"{roadmap.title} was removed from planner focus.",
            )

    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("roadmaps:detail", slug=roadmap.slug)
