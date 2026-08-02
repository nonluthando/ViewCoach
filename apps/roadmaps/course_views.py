from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .course_forms import (
    IBMSkillsBuildConfirmForm,
    IBMSkillsBuildImportForm,
)
from .course_services import (
    create_ibm_course_roadmap,
    format_course_outline,
    parse_course_outline_text,
)
from .ibm_client import IBMSkillsBuildClient, IBMImportError
from .models import ExternalCourseRoadmap, Roadmap
from .services import course_roadmap_cards, set_course_roadmap_focus


@login_required
def course_roadmap_list(request):
    return render(
        request,
        "roadmaps/course/course_roadmap_list.html",
        {"course_roadmaps": course_roadmap_cards(user=request.user)},
    )


@login_required
@require_http_methods(["GET", "POST"])
def ibm_course_import(request):
    form = IBMSkillsBuildImportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            preview = IBMSkillsBuildClient().fetch_course(
                form.cleaned_data["course_url"]
            )
        except IBMImportError as exc:
            form.add_error("course_url", str(exc))
        else:
            existing = (
                ExternalCourseRoadmap.objects.filter(
                    user=request.user,
                    provider=(
                        ExternalCourseRoadmap.Provider.IBM_SKILLSBUILD
                    ),
                    source_url=preview.source_url,
                )
                .select_related("roadmap")
                .first()
            )
            confirm_form = IBMSkillsBuildConfirmForm(
                initial={
                    "source_url": preview.source_url,
                    "title": preview.title,
                    "description": preview.description,
                    "outline_text": format_course_outline(preview.outline),
                }
            )
            return render(
                request,
                "roadmaps/course/ibm_course_preview.html",
                {
                    "preview": preview,
                    "existing": existing,
                    "confirm_form": confirm_form,
                },
            )
    return render(
        request,
        "roadmaps/course/ibm_course_import.html",
        {"form": form},
    )


@login_required
@require_POST
def ibm_course_confirm(request):
    form = IBMSkillsBuildConfirmForm(request.POST)
    if not form.is_valid():
        messages.error(
            request,
            "Review the course title and outline before importing.",
        )
        return redirect("roadmaps:ibm_course_import")
    try:
        preview = IBMSkillsBuildClient().fetch_course(
            form.cleaned_data["source_url"]
        )
    except IBMImportError as exc:
        messages.error(request, str(exc))
        return redirect("roadmaps:ibm_course_import")

    rows = parse_course_outline_text(form.cleaned_data["outline_text"])
    source, created = create_ibm_course_roadmap(
        user=request.user,
        preview=preview,
        title=form.cleaned_data["title"],
        description=form.cleaned_data["description"],
        outline_rows=rows,
    )
    if created:
        messages.success(
            request,
            f"Imported {source.roadmap.title} with {len(rows)} lessons.",
        )
    else:
        messages.info(
            request,
            "That IBM SkillsBuild course is already imported.",
        )
    return redirect("roadmaps:detail", slug=source.roadmap.slug)


@login_required
@require_POST
def toggle_course_focus(request, slug):
    source = get_object_or_404(
        ExternalCourseRoadmap.objects.select_related("roadmap"),
        user=request.user,
        roadmap__slug=slug,
        roadmap__source__in=[Roadmap.Source.IBM, Roadmap.Source.CUSTOM],
    )
    focused = request.POST.get("focused") == "true"
    enrolment = set_course_roadmap_focus(
        user=request.user,
        source=source,
        focused=focused,
    )
    if enrolment.is_focused:
        messages.success(
            request,
            f"{source.roadmap.title} can now appear in daily plans.",
        )
    else:
        messages.info(
            request,
            f"{source.roadmap.title} was removed from planner focus.",
        )
    return redirect(request.POST.get("next") or "roadmaps:course_list")


@login_required
@require_POST
def delete_course_roadmap(request, slug):
    source = get_object_or_404(
        ExternalCourseRoadmap.objects.select_related("roadmap"),
        user=request.user,
        roadmap__slug=slug,
        roadmap__source__in=[Roadmap.Source.IBM, Roadmap.Source.CUSTOM],
    )
    title = source.roadmap.title
    source.roadmap.delete()
    messages.success(
        request,
        (
            f"Removed {title} from ViewCoach. "
            "The original course was not changed."
        ),
    )
    return redirect("roadmaps:course_list")
