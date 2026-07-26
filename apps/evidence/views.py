from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.goals.models import InterviewGoal
from apps.questions.models import Question
from apps.roadmaps.models import RoadmapTopic

from .forms import (
    BehaviouralStoryForm,
    DecisionRecordForm,
    EvidenceItemForm,
    GoalEvidenceLinkForm,
    ProjectExplanationForm,
    QuestionEvidenceLinkForm,
    TopicEvidenceLinkForm,
    TopicEvidenceProfileForm,
)
from .models import (
    BehaviouralStory,
    DecisionRecord,
    EvidenceItem,
    GoalEvidenceLink,
    ProjectExplanation,
    QuestionEvidenceLink,
    TopicEvidenceLink,
    TopicEvidenceProfile,
)
from .services import filter_evidence_library


def _owned_evidence(user):
    return EvidenceItem.objects.filter(owner=user)


def _owned_item(user, evidence_id):
    return get_object_or_404(_owned_evidence(user), pk=evidence_id)


def _accessible_topic(user, topic_id):
    return get_object_or_404(
        RoadmapTopic.objects.select_related("section", "section__roadmap").filter(
            Q(section__roadmap__is_system=True)
            | Q(section__roadmap__created_by=user)
        ),
        pk=topic_id,
        section__roadmap__is_published=True,
    )


def _accessible_question(user, question_id):
    return get_object_or_404(
        Question.objects.filter(Q(is_system=True) | Q(owner=user)),
        pk=question_id,
    )


def _owned_goal(user, goal_id):
    return get_object_or_404(InterviewGoal, user=user, pk=goal_id)


@login_required
def evidence_list(request):
    search_term = request.GET.get("q", "").strip()
    source_type = request.GET.get("type", "").strip()
    evidence = filter_evidence_library(
        user=request.user,
        search_term=search_term,
        source_type=source_type,
    )
    page = Paginator(evidence, 16).get_page(request.GET.get("page"))
    return render(
        request,
        "evidence/evidence_list.html",
        {
            "page": page,
            "source_types": EvidenceItem.SourceType.choices,
            "filters": {"q": search_term, "type": source_type},
        },
    )


@login_required
def evidence_create(request):
    if request.method == "POST":
        form = EvidenceItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            messages.success(request, "Evidence record created.")
            return redirect(item)
    else:
        form = EvidenceItemForm()
    return render(
        request,
        "evidence/evidence_form.html",
        {"form": form, "is_editing": False},
    )


@login_required
def evidence_edit(request, evidence_id):
    item = _owned_item(request.user, evidence_id)
    if request.method == "POST":
        form = EvidenceItemForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, "Evidence record updated.")
            return redirect(item)
    else:
        form = EvidenceItemForm(instance=item)
    return render(
        request,
        "evidence/evidence_form.html",
        {"form": form, "item": item, "is_editing": True},
    )


@login_required
def evidence_detail(request, evidence_id):
    item = _owned_item(request.user, evidence_id)
    return render(
        request,
        "evidence/evidence_detail.html",
        {
            "item": item,
            "decisions": item.decisions.all(),
            "stories": item.behavioural_stories.all(),
            "topic_links": item.topic_links.select_related(
                "profile__topic__section__roadmap"
            ),
            "question_links": item.question_links.select_related("question"),
            "goal_links": item.goal_links.select_related("goal"),
            "decision_form": DecisionRecordForm(),
            "story_form": BehaviouralStoryForm(),
        },
    )


@login_required
def interview_pack(request):
    projects = (
        _owned_evidence(request.user)
        .filter(source_type=EvidenceItem.SourceType.PROJECT)
        .prefetch_related("goal_links__goal")
        .order_by("-updated_at", "title")
    )
    project_cards = []
    for project in projects:
        explanation = ProjectExplanation.objects.filter(evidence=project).first()
        project_cards.append(
            {
                "project": project,
                "explanation": explanation,
                "goal_links": project.goal_links.all(),
            }
        )

    return render(
        request,
        "evidence/interview_pack.html",
        {"project_cards": project_cards},
    )


@login_required
def project_explanation_edit(request, evidence_id):
    item = get_object_or_404(
        _owned_evidence(request.user),
        pk=evidence_id,
        source_type=EvidenceItem.SourceType.PROJECT,
    )
    explanation = ProjectExplanation.objects.filter(evidence=item).first()

    if request.method == "POST":
        form = ProjectExplanationForm(request.POST, instance=explanation)
        if form.is_valid():
            explanation = form.save(commit=False)
            explanation.evidence = item
            explanation.save()
            messages.success(request, "Project interview explanation saved.")
            return redirect("evidence:interview_pack")
    else:
        form = ProjectExplanationForm(instance=explanation)

    return render(
        request,
        "evidence/project_explanation_form.html",
        {
            "form": form,
            "item": item,
            "is_editing": explanation is not None,
        },
    )


@login_required
def evidence_delete(request, evidence_id):
    item = _owned_item(request.user, evidence_id)
    if request.method == "POST":
        title = item.title
        item.delete()
        messages.success(request, f"Deleted evidence record: {title}.")
        return redirect("evidence:list")
    return render(request, "evidence/evidence_confirm_delete.html", {"item": item})


@login_required
@require_POST
def decision_add(request, evidence_id):
    item = _owned_item(request.user, evidence_id)
    form = DecisionRecordForm(request.POST)
    if form.is_valid():
        decision = form.save(commit=False)
        decision.evidence = item
        decision.save()
        messages.success(request, "Decision record added.")
    else:
        messages.error(request, "Check the decision details and try again.")
    return redirect(item)


@login_required
@require_POST
def decision_delete(request, evidence_id, decision_id):
    item = _owned_item(request.user, evidence_id)
    decision = get_object_or_404(DecisionRecord, evidence=item, pk=decision_id)
    decision.delete()
    messages.success(request, "Decision record removed.")
    return redirect(item)


@login_required
@require_POST
def story_add(request, evidence_id):
    item = _owned_item(request.user, evidence_id)
    form = BehaviouralStoryForm(request.POST)
    if form.is_valid():
        story = form.save(commit=False)
        story.evidence = item
        story.save()
        messages.success(request, "Behavioural story added.")
    else:
        messages.error(request, "Check the story details and try again.")
    return redirect(item)


@login_required
@require_POST
def story_delete(request, evidence_id, story_id):
    item = _owned_item(request.user, evidence_id)
    story = get_object_or_404(BehaviouralStory, evidence=item, pk=story_id)
    story.delete()
    messages.success(request, "Behavioural story removed.")
    return redirect(item)


@login_required
@require_POST
def topic_profile_save(request, topic_id):
    topic = _accessible_topic(request.user, topic_id)
    profile, _ = TopicEvidenceProfile.objects.get_or_create(
        user=request.user,
        topic=topic,
    )
    form = TopicEvidenceProfileForm(request.POST, instance=profile)
    if form.is_valid():
        form.save()
        messages.success(request, "Personal interview angle saved.")
    else:
        messages.error(request, "Check the personal evidence fields and try again.")
    return redirect(
        "roadmaps:topic_detail",
        slug=topic.section.roadmap.slug,
        topic_id=topic.pk,
    )


@login_required
@require_POST
def topic_evidence_link(request, topic_id):
    topic = _accessible_topic(request.user, topic_id)
    profile, _ = TopicEvidenceProfile.objects.get_or_create(
        user=request.user,
        topic=topic,
    )
    form = TopicEvidenceLinkForm(request.POST, user=request.user)
    if form.is_valid():
        try:
            TopicEvidenceLink.objects.create(
                profile=profile,
                evidence=form.cleaned_data["evidence"],
                connection_note=form.cleaned_data["connection_note"],
            )
        except IntegrityError:
            messages.info(request, "That evidence is already linked to this topic.")
        else:
            messages.success(request, "Evidence linked to this roadmap topic.")
    else:
        messages.error(request, "Choose one of your evidence records.")
    return redirect(
        "roadmaps:topic_detail",
        slug=topic.section.roadmap.slug,
        topic_id=topic.pk,
    )


@login_required
@require_POST
def topic_evidence_unlink(request, topic_id, link_id):
    topic = _accessible_topic(request.user, topic_id)
    link = get_object_or_404(
        TopicEvidenceLink,
        profile__user=request.user,
        profile__topic=topic,
        pk=link_id,
    )
    link.delete()
    messages.success(request, "Evidence unlinked from this topic.")
    return redirect(
        "roadmaps:topic_detail",
        slug=topic.section.roadmap.slug,
        topic_id=topic.pk,
    )


@login_required
@require_POST
def question_evidence_link(request, question_id):
    question = _accessible_question(request.user, question_id)
    form = QuestionEvidenceLinkForm(request.POST, user=request.user)
    if form.is_valid():
        try:
            QuestionEvidenceLink.objects.create(
                user=request.user,
                question=question,
                evidence=form.cleaned_data["evidence"],
                answer_angle=form.cleaned_data["answer_angle"],
            )
        except IntegrityError:
            messages.info(request, "That evidence is already linked to this question.")
        else:
            messages.success(request, "Evidence linked to this question.")
    else:
        messages.error(request, "Choose one of your evidence records.")
    return redirect("questions:detail", pk=question.pk)


@login_required
@require_POST
def question_evidence_unlink(request, question_id, link_id):
    question = _accessible_question(request.user, question_id)
    link = get_object_or_404(
        QuestionEvidenceLink,
        user=request.user,
        question=question,
        pk=link_id,
    )
    link.delete()
    messages.success(request, "Evidence unlinked from this question.")
    return redirect("questions:detail", pk=question.pk)


@login_required
@require_POST
def goal_evidence_link(request, goal_id):
    goal = _owned_goal(request.user, goal_id)
    form = GoalEvidenceLinkForm(request.POST, user=request.user)
    if form.is_valid():
        try:
            GoalEvidenceLink.objects.create(
                user=request.user,
                goal=goal,
                evidence=form.cleaned_data["evidence"],
                relevance=form.cleaned_data["relevance"],
                framing_notes=form.cleaned_data["framing_notes"],
            )
        except IntegrityError:
            messages.info(request, "That evidence is already linked to this goal.")
        else:
            messages.success(request, "Evidence linked to this interview goal.")
    else:
        messages.error(request, "Choose one of your evidence records.")
    return redirect(goal)


@login_required
@require_POST
def goal_evidence_unlink(request, goal_id, link_id):
    goal = _owned_goal(request.user, goal_id)
    link = get_object_or_404(
        GoalEvidenceLink,
        user=request.user,
        goal=goal,
        pk=link_id,
    )
    link.delete()
    messages.success(request, "Evidence unlinked from this goal.")
    return redirect(goal)
