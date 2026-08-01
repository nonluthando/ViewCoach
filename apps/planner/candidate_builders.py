"""Build database-backed candidates and convert selections to plan payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.utils import timezone

from apps.goals.models import InterviewGoal
from apps.questions.models import Question, TechnicalQuestion
from apps.reviews.models import ReviewAttempt
from apps.reviews.services import due_review_states
from apps.roadmaps.models import RoadmapTopic, UserRoadmap, UserTopicProgress

from .candidates import CandidateKind, PlanCandidate, stable_candidate_id
from .explanations import candidate_explanation
from .models import StudyRecommendation
from .policies import (
    MAX_REVIEW_GROUPS,
    PRACTICE_BLOCK_MAX_MINUTES,
    PRACTICE_BLOCK_MINUTES,
    REVIEW_MINUTES_PER_QUESTION,
    ROADMAP_BLOCK_MAX_MINUTES,
    ROADMAP_BLOCK_MINUTES,
    WEAK_AREA_BLOCK_MINUTES,
    DailyPlanPolicy,
    plan_policy_for_budget,
)
from .scoring import BASE_SCORE_BY_KIND, KIND_ORDER

MAX_CANDIDATE_ROADMAPS = 8
MAX_REVIEW_QUESTIONS_PER_GROUP = 8
MAX_WEAK_AREA_CANDIDATES = 8
MAX_PRACTICE_CANDIDATES = 24
LIBRARY_MINUTES = 15


@dataclass(slots=True)
class CandidateBuildResult:
    candidates: tuple[PlanCandidate, ...]
    policy: DailyPlanPolicy
    question_by_id: dict[int, Question]
    topic_by_id: dict[int, RoadmapTopic]
    goal: InterviewGoal | None


def _primary_goal(*, user):
    return (
        InterviewGoal.objects.filter(
            user=user,
            status=InterviewGoal.Status.ACTIVE,
            is_primary=True,
        )
        .prefetch_related("roadmaps", "stages")
        .first()
    )


def _ordered_active_roadmap_enrolments(*, user, goal=None):
    enrolment_query = UserRoadmap.objects.filter(
        user=user,
        status=UserRoadmap.Status.IN_PROGRESS,
        roadmap__is_published=True,
    ).select_related("roadmap")

    if goal is not None:
        linked_roadmap_ids = list(goal.roadmaps.values_list("pk", flat=True))
        if linked_roadmap_ids:
            enrolment_query = enrolment_query.filter(roadmap_id__in=linked_roadmap_ids)

    enrolments = list(enrolment_query)
    if not enrolments:
        return []

    roadmap_ids = [enrolment.roadmap_id for enrolment in enrolments]
    in_progress_roadmap_ids = set(
        UserTopicProgress.objects.filter(
            user=user,
            status=UserTopicProgress.Status.IN_PROGRESS,
            topic__section__roadmap_id__in=roadmap_ids,
        ).values_list("topic__section__roadmap_id", flat=True)
    )
    completed_counts = {
        roadmap_id: UserTopicProgress.objects.filter(
            user=user,
            status=UserTopicProgress.Status.COMPLETED,
            topic__section__roadmap_id=roadmap_id,
        ).count()
        for roadmap_id in roadmap_ids
    }
    topic_counts = {
        roadmap_id: RoadmapTopic.objects.filter(
            section__roadmap_id=roadmap_id,
        ).count()
        for roadmap_id in roadmap_ids
    }
    enrolments = [
        enrolment
        for enrolment in enrolments
        if completed_counts.get(enrolment.roadmap_id, 0) < topic_counts.get(enrolment.roadmap_id, 0)
    ]

    far_future = date.max
    enrolments.sort(
        key=lambda enrolment: (
            0 if enrolment.roadmap_id in in_progress_roadmap_ids else 1,
            completed_counts.get(enrolment.roadmap_id, 0)
            / max(topic_counts.get(enrolment.roadmap_id, 0), 1),
            enrolment.target_date or far_future,
            enrolment.started_at or timezone.now(),
            enrolment.pk,
        )
    )
    return enrolments


def _unfinished_roadmap_topics(*, user, enrolment):
    topic_ordering = (
        "section__position",
        "position",
        "section__title",
        "title",
        "pk",
    )
    topics = RoadmapTopic.objects.filter(
        section__roadmap=enrolment.roadmap,
    ).select_related("section", "section__roadmap")

    completed_topic_ids = UserTopicProgress.objects.filter(
        user=user,
        status=UserTopicProgress.Status.COMPLETED,
        topic__section__roadmap=enrolment.roadmap,
    ).values_list("topic_id", flat=True)

    in_progress_ids = set(
        UserTopicProgress.objects.filter(
            user=user,
            status=UserTopicProgress.Status.IN_PROGRESS,
            topic__section__roadmap=enrolment.roadmap,
        ).values_list("topic_id", flat=True)
    )

    available = topics.exclude(pk__in=completed_topic_ids)
    return (
        sorted(
            available.order_by(*topic_ordering),
            key=lambda topic: 0 if topic.pk in in_progress_ids else 1,
        ),
        in_progress_ids,
    )


def _question_context(question):
    if question.question_type == Question.Type.TECHNICAL:
        topic = getattr(question.specific, "topic", "").strip()
        if topic:
            return f"technical:{topic.casefold()}", topic

    labels = {
        Question.Type.TECHNICAL: "Technical concepts",
        Question.Type.CONCEPT: "Concept questions",
        Question.Type.BEHAVIOURAL: "Behavioural questions",
        Question.Type.DEBUG: "Debugging and repository tasks",
    }
    label = labels.get(question.question_type, "Interview questions")
    return question.question_type.casefold(), label


def _normalised_words(value):
    return {
        word.strip(".,:;()[]{}").casefold()
        for word in value.replace("/", " ").replace("-", " ").split()
        if len(word.strip(".,:;()[]{}")) >= 4
    }


def _build_review_candidates(
    *,
    due_states,
    policy,
    now,
    candidates,
    question_by_id,
):
    if not due_states or policy.review_target_minutes <= 0:
        return set()

    max_questions = max(
        1,
        policy.review_target_minutes // REVIEW_MINUTES_PER_QUESTION,
    )
    groups = {}

    for state in due_states:
        if sum(len(group["states"]) for group in groups.values()) >= max_questions:
            break

        key, label = _question_context(state.question)
        if key not in groups:
            if len(groups) >= MAX_REVIEW_GROUPS:
                continue
            groups[key] = {"label": label, "states": []}

        if len(groups[key]["states"]) >= MAX_REVIEW_QUESTIONS_PER_GROUP:
            continue

        groups[key]["states"].append(state)

    selected_question_ids = set()
    for key, group in groups.items():
        states = group["states"]
        if not states:
            continue

        question_ids = tuple(state.question_id for state in states)
        selected_question_ids.update(question_ids)
        question_by_id.update({state.question_id: state.question for state in states})
        question_count = len(states)
        question_label = "question" if question_count == 1 else "questions"

        candidates.append(
            PlanCandidate(
                candidate_id=stable_candidate_id(
                    kind=CandidateKind.REVIEW,
                    source=key,
                    source_ids=question_ids,
                ),
                kind=CandidateKind.REVIEW,
                title=(f"Review: {group['label']} — {question_count} {question_label}"),
                estimated_minutes=(question_count * REVIEW_MINUTES_PER_QUESTION),
                question_ids=question_ids,
                context_key=f"review:{key}",
                is_overdue=any(state.due_at < now for state in states),
                description=("Complete this related review group before switching domains."),
                rationale=(
                    "Due reviews are time-sensitive and grouped to reduce context switching."
                ),
            )
        )

    return selected_question_ids


def _build_roadmap_candidates(
    *,
    user,
    goal,
    plan_date,
    policy,
    candidates,
    topic_by_id,
):
    if policy.max_roadmaps <= 0:
        return []

    enrolments = _ordered_active_roadmap_enrolments(user=user, goal=goal)
    enrolments = enrolments[:MAX_CANDIDATE_ROADMAPS]
    linked_roadmap_ids = (
        set(goal.roadmaps.values_list("pk", flat=True)) if goal is not None else set()
    )

    for enrolment in enrolments:
        topics, in_progress_ids = _unfinished_roadmap_topics(
            user=user,
            enrolment=enrolment,
        )
        candidate_topics = topics[: policy.max_topics_per_roadmap]

        goal_deadline = goal.next_deadline if goal is not None else None
        target_date = goal_deadline or enrolment.target_date
        deadline_days = (target_date - plan_date).days if target_date is not None else None

        for topic in candidate_topics:
            topic_by_id[topic.pk] = topic
            candidates.append(
                PlanCandidate(
                    candidate_id=stable_candidate_id(
                        kind=CandidateKind.ROADMAP,
                        source=f"roadmap-{enrolment.roadmap_id}",
                        source_ids=(topic.pk,),
                    ),
                    kind=CandidateKind.ROADMAP,
                    title=f"Learn: {topic.title}",
                    estimated_minutes=ROADMAP_BLOCK_MINUTES,
                    roadmap_id=enrolment.roadmap_id,
                    topic_ids=(topic.pk,),
                    goal_id=goal.pk if goal is not None else None,
                    context_key=f"roadmap:{enrolment.roadmap_id}",
                    supports_primary_goal=(enrolment.roadmap_id in linked_roadmap_ids),
                    continues_in_progress_work=topic.pk in in_progress_ids,
                    deadline_days=deadline_days,
                    description=(
                        "Spend one focused block moving the "
                        f"{enrolment.roadmap.title} roadmap forward."
                    ),
                    rationale=(
                        "This is a coherent learning block, not a quick "
                        "topic skim."
                        + (
                            f" It supports your primary goal: {goal.title}."
                            if goal is not None
                            else ""
                        )
                    ),
                )
            )

    return enrolments


def _build_weak_area_candidates(
    *,
    user,
    now,
    excluded_question_ids,
    policy,
    candidates,
    question_by_id,
):
    if policy.practice_target_minutes < WEAK_AREA_BLOCK_MINUTES or policy.max_weak_area_blocks <= 0:
        return

    recent_cutoff = now - timedelta(days=14)
    attempts = (
        ReviewAttempt.objects.filter(
            state__user=user,
            state__question__owner=user,
            state__question__status=Question.Status.READY_FOR_REVIEW,
            rating__in=[
                ReviewAttempt.Rating.AGAIN,
                ReviewAttempt.Rating.HARD,
            ],
            reviewed_at__gte=recent_cutoff,
        )
        .exclude(state__question_id__in=excluded_question_ids)
        .select_related(
            "state__question",
            "state__question__technicalquestion",
            "state__question__conceptquestion",
            "state__question__behaviouralquestion",
            "state__question__debugquestion",
        )
        .order_by("-reviewed_at", "-pk")
    )

    seen_question_ids = set()
    for attempt in attempts[:100]:
        question = attempt.state.question
        if question.pk in seen_question_ids:
            continue

        seen_question_ids.add(question.pk)
        question_by_id[question.pk] = question
        context_key, _ = _question_context(question)
        candidates.append(
            PlanCandidate(
                candidate_id=stable_candidate_id(
                    kind=CandidateKind.WEAK_AREA,
                    source="recent-performance",
                    source_ids=(question.pk,),
                ),
                kind=CandidateKind.WEAK_AREA,
                title=f"Revisit: {question.title}",
                estimated_minutes=WEAK_AREA_BLOCK_MINUTES,
                question_ids=(question.pk,),
                context_key=f"weak:{context_key}",
                is_recently_hard=True,
                description=(
                    "Review the explanation, mistakes and approach without "
                    "changing its spaced-review schedule."
                ),
                rationale=(
                    "Your recent recall was rated "
                    f"{attempt.get_rating_display()}, so this is a useful "
                    "focused reset."
                ),
            )
        )
        if len(seen_question_ids) >= MAX_WEAK_AREA_CANDIDATES:
            break


def _build_practice_candidates(
    *,
    user,
    goal,
    plan_date,
    enrolments,
    excluded_question_ids,
    policy,
    candidates,
    question_by_id,
):
    if policy.practice_target_minutes < PRACTICE_BLOCK_MINUTES or policy.max_practice_blocks <= 0:
        return

    questions = list(
        TechnicalQuestion.objects.filter(is_system=True)
        .exclude(pk__in=excluded_question_ids)
        .order_by("system_key", "pk")
    )
    if not questions:
        return

    offset = (plan_date.toordinal() + (user.pk or 0)) % len(questions)
    questions = questions[offset:] + questions[:offset]

    goal_words = _normalised_words(f"{goal.role_title} {goal.title}") if goal is not None else set()
    roadmap_words = set()
    for enrolment in enrolments:
        roadmap_words.update(_normalised_words(enrolment.roadmap.title))

    for question in questions[:MAX_PRACTICE_CANDIDATES]:
        question_by_id[question.pk] = question
        question_words = _normalised_words(f"{question.title} {question.topic} {question.pattern}")
        topic_label = question.topic.strip() or "Technical practice"

        candidates.append(
            PlanCandidate(
                candidate_id=stable_candidate_id(
                    kind=CandidateKind.PRACTICE,
                    source="built-in",
                    source_ids=(question.pk,),
                ),
                kind=CandidateKind.PRACTICE,
                title=f"Practise: {question.title}",
                estimated_minutes=PRACTICE_BLOCK_MINUTES,
                question_ids=(question.pk,),
                goal_id=goal.pk if goal is not None else None,
                context_key=f"practice:{topic_label.casefold()}",
                supports_primary_goal=bool(goal_words & question_words),
                continues_in_progress_work=bool(roadmap_words & question_words),
                description=(
                    "Work through one fresh built-in question and explain "
                    "the approach before reading the notes."
                ),
                rationale=(
                    "A fresh question adds retrieval practice while keeping the session balanced."
                ),
            )
        )


def _build_library_candidate(
    *,
    user,
    time_budget_minutes,
    candidates,
    question_by_id,
):
    if candidates:
        return

    incomplete_question = (
        Question.objects.filter(
            owner=user,
            is_system=False,
            status=Question.Status.NEEDS_NOTES,
        )
        .order_by("-updated_at", "pk")
        .first()
    )

    estimated_minutes = max(
        1,
        min(LIBRARY_MINUTES, int(time_budget_minutes)),
    )
    if incomplete_question is not None:
        question_by_id[incomplete_question.pk] = incomplete_question
        candidates.append(
            PlanCandidate(
                candidate_id=stable_candidate_id(
                    kind=CandidateKind.LIBRARY,
                    source="incomplete-question",
                    source_ids=(incomplete_question.pk,),
                ),
                kind=CandidateKind.LIBRARY,
                title=f"Finish preparing: {incomplete_question.title}",
                estimated_minutes=estimated_minutes,
                question_ids=(incomplete_question.pk,),
                description=(
                    "Complete the missing explanation or solution notes, "
                    "then mark it ready for review."
                ),
                rationale=(
                    "Preparing one question creates useful material for future review sessions."
                ),
            )
        )
        return

    candidates.append(
        PlanCandidate(
            candidate_id="library:add-question",
            kind=CandidateKind.LIBRARY,
            title="Add one interview question",
            estimated_minutes=estimated_minutes,
            description=(
                "Capture a real question and the reasoning you would want "
                "to explain under pressure."
            ),
            rationale=(
                "Your plan needs study material before review scheduling can become useful."
            ),
        )
    )


def build_plan_candidates(
    *,
    user,
    time_budget_minutes,
    plan_date,
    now,
):
    due_states = list(due_review_states(user=user, now=now))
    policy = plan_policy_for_budget(
        time_budget_minutes=time_budget_minutes,
        due_count=len(due_states),
    )
    goal = _primary_goal(user=user)

    candidates = []
    question_by_id = {}
    topic_by_id = {}

    due_question_ids = _build_review_candidates(
        due_states=due_states,
        policy=policy,
        now=now,
        candidates=candidates,
        question_by_id=question_by_id,
    )
    enrolments = _build_roadmap_candidates(
        user=user,
        goal=goal,
        plan_date=plan_date,
        policy=policy,
        candidates=candidates,
        topic_by_id=topic_by_id,
    )
    _build_weak_area_candidates(
        user=user,
        now=now,
        excluded_question_ids=due_question_ids,
        policy=policy,
        candidates=candidates,
        question_by_id=question_by_id,
    )
    _build_practice_candidates(
        user=user,
        goal=goal,
        plan_date=plan_date,
        enrolments=enrolments,
        excluded_question_ids=set(question_by_id),
        policy=policy,
        candidates=candidates,
        question_by_id=question_by_id,
    )
    _build_library_candidate(
        user=user,
        time_budget_minutes=time_budget_minutes,
        candidates=candidates,
        question_by_id=question_by_id,
    )

    return CandidateBuildResult(
        candidates=tuple(candidates),
        policy=policy,
        question_by_id=question_by_id,
        topic_by_id=topic_by_id,
        goal=goal,
    )


def _extend_payload_blocks(*, payloads, time_budget_minutes):
    minutes_left = max(
        0,
        int(time_budget_minutes) - sum(payload["estimated_minutes"] for payload in payloads),
    )

    roadmap_payloads = [
        payload for payload in payloads if payload["kind"] == StudyRecommendation.Kind.ROADMAP
    ]
    while minutes_left >= PRACTICE_BLOCK_MINUTES and roadmap_payloads:
        extended = False
        for payload in roadmap_payloads:
            room = ROADMAP_BLOCK_MAX_MINUTES - payload["estimated_minutes"]
            if room < PRACTICE_BLOCK_MINUTES:
                continue
            increment = min(PRACTICE_BLOCK_MINUTES, room, minutes_left)
            payload["estimated_minutes"] += increment
            minutes_left -= increment
            extended = True
            if minutes_left < PRACTICE_BLOCK_MINUTES:
                break
        if not extended:
            break

    practice_payloads = [
        payload for payload in payloads if payload["kind"] == StudyRecommendation.Kind.PRACTICE
    ]
    while minutes_left >= PRACTICE_BLOCK_MINUTES and practice_payloads:
        extended = False
        for payload in practice_payloads:
            room = PRACTICE_BLOCK_MAX_MINUTES - payload["estimated_minutes"]
            if room < PRACTICE_BLOCK_MINUTES:
                continue
            increment = min(PRACTICE_BLOCK_MINUTES, room, minutes_left)
            payload["estimated_minutes"] += increment
            minutes_left -= increment
            extended = True
            if minutes_left < PRACTICE_BLOCK_MINUTES:
                break
        if not extended:
            break


def recommendation_payloads_from_selection(
    *,
    build_result,
    selection_result,
    time_budget_minutes,
):
    selected = sorted(
        selection_result.selected,
        key=lambda item: (
            KIND_ORDER[item.candidate.kind],
            -item.total_score,
            item.candidate.candidate_id,
        ),
    )

    payloads = []
    for scored_candidate in selected:
        candidate = scored_candidate.candidate
        first_question_id = candidate.question_ids[0] if candidate.question_ids else None
        first_topic_id = candidate.topic_ids[0] if candidate.topic_ids else None

        payload = {
            "kind": StudyRecommendation.Kind(candidate.kind.value),
            "title": candidate.title,
            "description": candidate.description,
            "rationale": candidate_explanation(scored_candidate),
            "estimated_minutes": candidate.estimated_minutes,
            "priority_score": BASE_SCORE_BY_KIND[candidate.kind],
        }
        if first_question_id is not None:
            payload["question"] = build_result.question_by_id[first_question_id]
        if first_topic_id is not None:
            payload["topic"] = build_result.topic_by_id[first_topic_id]

        payloads.append(payload)

    _extend_payload_blocks(
        payloads=payloads,
        time_budget_minutes=time_budget_minutes,
    )
    return payloads
