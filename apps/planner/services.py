from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.questions.models import Question, TechnicalQuestion
from apps.reviews.models import ReviewAttempt
from apps.reviews.services import due_review_states
from apps.roadmaps.models import RoadmapTopic, UserRoadmap, UserTopicProgress

from .models import StudyPlan, StudyRecommendation, StudySession

DEFAULT_TIME_BUDGET_MINUTES = 60
REVIEW_MINUTES_PER_QUESTION = 3
ROADMAP_TOPIC_MINUTES = 25
WEAK_AREA_MINUTES = 10
PRACTICE_MINUTES = 20
LIBRARY_MINUTES = 15


def _active_roadmap_enrolment(*, user):
    enrolments = list(
        UserRoadmap.objects.filter(
            user=user,
            status=UserRoadmap.Status.IN_PROGRESS,
            roadmap__is_published=True,
        ).select_related("roadmap")
    )
    if not enrolments:
        return None

    far_future = date.max
    enrolments.sort(
        key=lambda enrolment: (
            enrolment.target_date or far_future,
            enrolment.started_at or timezone.now(),
            enrolment.pk,
        )
    )
    return enrolments[0]


def _next_roadmap_topic(*, user, enrolment):
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

    in_progress = topics.filter(
        user_progress__user=user,
        user_progress__status=UserTopicProgress.Status.IN_PROGRESS,
    ).order_by(*topic_ordering).first()
    if in_progress is not None:
        return in_progress

    completed_topic_ids = UserTopicProgress.objects.filter(
        user=user,
        status=UserTopicProgress.Status.COMPLETED,
        topic__section__roadmap=enrolment.roadmap,
    ).values_list("topic_id", flat=True)
    return (
        topics.exclude(pk__in=completed_topic_ids)
        .order_by(*topic_ordering)
        .first()
    )


def _recent_weak_question(*, user, excluded_question_ids, now):
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
        .select_related("state__question")
        .order_by("-reviewed_at", "-pk")
    )

    seen_question_ids = set()
    for attempt in attempts[:50]:
        question = attempt.state.question
        if question.pk in seen_question_ids:
            continue
        seen_question_ids.add(question.pk)
        return question, attempt
    return None, None


def _practice_question(*, user, topic, excluded_question_ids, plan_date):
    questions = TechnicalQuestion.objects.filter(is_system=True).exclude(
        pk__in=excluded_question_ids
    )

    if topic is not None:
        topic_words = [
            word.strip(".,:;()[]").lower()
            for word in topic.title.split()
            if len(word.strip(".,:;()[]")) >= 4
        ]
        topic_filter = Q()
        for word in topic_words[:4]:
            topic_filter |= Q(title__icontains=word)
            topic_filter |= Q(topic__icontains=word)
            topic_filter |= Q(pattern__icontains=word)
        if topic_words:
            matched_question = questions.filter(topic_filter).order_by(
                "system_key",
                "pk",
            ).first()
            if matched_question is not None:
                return matched_question

    candidate_ids = list(
        questions.order_by("system_key", "pk").values_list("pk", flat=True)
    )
    if not candidate_ids:
        return None

    user_seed = user.pk or 0
    selected_index = (plan_date.toordinal() + user_seed) % len(candidate_ids)
    return questions.get(pk=candidate_ids[selected_index])


def _recommendation_payloads(*, user, time_budget_minutes, plan_date, now):
    remaining_minutes = time_budget_minutes
    payloads = []
    selected_question_ids = set()

    due_states = list(due_review_states(user=user, now=now))
    due_count = len(due_states)
    if due_count:
        review_capacity = max(1, remaining_minutes // REVIEW_MINUTES_PER_QUESTION)
        planned_review_count = min(due_count, review_capacity)
        estimated_minutes = planned_review_count * REVIEW_MINUTES_PER_QUESTION
        first_question = due_states[0].question
        selected_question_ids.update(
            state.question_id for state in due_states[:planned_review_count]
        )
        if planned_review_count < due_count:
            review_title = (
                f"Review {planned_review_count} of {due_count} due questions"
            )
        else:
            review_title = f"Review {planned_review_count} due question"
            if planned_review_count != 1:
                review_title += "s"
        payloads.append(
            {
                "kind": StudyRecommendation.Kind.REVIEW,
                "title": review_title,
                "description": (
                    "Begin with the material whose review window has arrived. "
                    f"Allow roughly {REVIEW_MINUTES_PER_QUESTION} minutes per question."
                ),
                "rationale": (
                    "Due reviews are time-sensitive, so they receive the highest priority."
                ),
                "estimated_minutes": estimated_minutes,
                "priority_score": 100,
                "question": first_question,
            }
        )
        remaining_minutes = max(0, remaining_minutes - estimated_minutes)

    enrolment = _active_roadmap_enrolment(user=user)
    next_topic = None
    if enrolment is not None:
        next_topic = _next_roadmap_topic(user=user, enrolment=enrolment)

    if next_topic is not None and remaining_minutes >= 15:
        estimated_minutes = min(ROADMAP_TOPIC_MINUTES, remaining_minutes)
        deadline_note = ""
        priority_score = 80
        if enrolment.target_date:
            days_remaining = (enrolment.target_date - plan_date).days
            if 0 <= days_remaining <= 14:
                priority_score += 10
                deadline_note = f" Your target date is {days_remaining} days away."
        payloads.append(
            {
                "kind": StudyRecommendation.Kind.ROADMAP,
                "title": f"Continue: {next_topic.title}",
                "description": (
                    f"Move the {enrolment.roadmap.title} roadmap forward by one focused topic."
                ),
                "rationale": (
                    "This is the next unfinished topic in your active roadmap."
                    f"{deadline_note}"
                ),
                "estimated_minutes": estimated_minutes,
                "priority_score": priority_score,
                "topic": next_topic,
            }
        )
        remaining_minutes -= estimated_minutes

    weak_question, weak_attempt = _recent_weak_question(
        user=user,
        excluded_question_ids=selected_question_ids,
        now=now,
    )
    if weak_question is not None and remaining_minutes >= WEAK_AREA_MINUTES:
        payloads.append(
            {
                "kind": StudyRecommendation.Kind.WEAK_AREA,
                "title": f"Revisit: {weak_question.title}",
                "description": (
                    "Review the explanation, mistakes and approach without changing its "
                    "spaced-review schedule."
                ),
                "rationale": (
                    f"Your recent recall was rated {weak_attempt.get_rating_display()}, "
                    "so this is a useful place for a short reset."
                ),
                "estimated_minutes": WEAK_AREA_MINUTES,
                "priority_score": 70,
                "question": weak_question,
            }
        )
        selected_question_ids.add(weak_question.pk)
        remaining_minutes -= WEAK_AREA_MINUTES

    if remaining_minutes >= 15:
        practice_question = _practice_question(
            user=user,
            topic=next_topic,
            excluded_question_ids=selected_question_ids,
            plan_date=plan_date,
        )
        if practice_question is not None:
            estimated_minutes = min(PRACTICE_MINUTES, remaining_minutes)
            payloads.append(
                {
                    "kind": StudyRecommendation.Kind.PRACTICE,
                    "title": f"Practise: {practice_question.title}",
                    "description": (
                        "Work through one fresh built-in question and explain the approach "
                        "before reading the notes."
                    ),
                    "rationale": (
                        "A fresh question adds retrieval practice while keeping the "
                        "session balanced."
                    ),
                    "estimated_minutes": estimated_minutes,
                    "priority_score": 50,
                    "question": practice_question,
                }
            )
            remaining_minutes -= estimated_minutes

    if not payloads:
        incomplete_question = (
            Question.objects.filter(
                owner=user,
                is_system=False,
                status=Question.Status.NEEDS_NOTES,
            )
            .order_by("-updated_at", "pk")
            .first()
        )
        if incomplete_question is not None:
            payloads.append(
                {
                    "kind": StudyRecommendation.Kind.LIBRARY,
                    "title": f"Finish preparing: {incomplete_question.title}",
                    "description": (
                        "Complete the missing explanation or solution notes, then mark it ready "
                        "for review."
                    ),
                    "rationale": (
                        "Preparing one question creates useful material for future review sessions."
                    ),
                    "estimated_minutes": min(LIBRARY_MINUTES, time_budget_minutes),
                    "priority_score": 30,
                    "question": incomplete_question,
                }
            )
        else:
            payloads.append(
                {
                    "kind": StudyRecommendation.Kind.LIBRARY,
                    "title": "Add one interview question",
                    "description": (
                        "Capture a real question and the reasoning you would want to explain "
                        "under pressure."
                    ),
                    "rationale": (
                        "Your plan needs study material before review scheduling can become useful."
                    ),
                    "estimated_minutes": min(LIBRARY_MINUTES, time_budget_minutes),
                    "priority_score": 20,
                }
            )

    return payloads


@transaction.atomic
def generate_daily_plan(
    *,
    user,
    time_budget_minutes=DEFAULT_TIME_BUDGET_MINUTES,
    now=None,
    force=False,
):
    current_time = now or timezone.now()
    plan_date = timezone.localdate(current_time)
    plan, created = StudyPlan.objects.select_for_update().get_or_create(
        user=user,
        plan_date=plan_date,
        defaults={
            "time_budget_minutes": time_budget_minutes,
            "generated_at": current_time,
        },
    )

    should_regenerate = created or force or not plan.recommendations.exists()
    if not should_regenerate:
        return plan

    plan.recommendations.all().delete()
    plan.time_budget_minutes = time_budget_minutes
    plan.status = StudyPlan.Status.ACTIVE
    plan.generated_at = current_time
    plan.save(
        update_fields=[
            "time_budget_minutes",
            "status",
            "generated_at",
            "updated_at",
        ]
    )

    payloads = _recommendation_payloads(
        user=user,
        time_budget_minutes=time_budget_minutes,
        plan_date=plan_date,
        now=current_time,
    )
    StudyRecommendation.objects.bulk_create(
        [
            StudyRecommendation(
                plan=plan,
                position=position,
                **payload,
            )
            for position, payload in enumerate(payloads, start=1)
        ]
    )
    return plan


def plan_summary(*, plan):
    recommendations = list(
        plan.recommendations.select_related(
            "question",
            "topic__section__roadmap",
        )
    )
    completed_count = sum(
        recommendation.completed_at is not None
        for recommendation in recommendations
    )
    return {
        "plan": plan,
        "recommendations": recommendations,
        "total_count": len(recommendations),
        "completed_count": completed_count,
        "estimated_minutes": sum(
            recommendation.estimated_minutes
            for recommendation in recommendations
        ),
        "is_complete": bool(recommendations)
        and completed_count == len(recommendations),
    }


def sync_plan_status(*, plan):
    recommendations = plan.recommendations.all()
    has_recommendations = recommendations.exists()
    is_complete = has_recommendations and not recommendations.filter(
        completed_at__isnull=True
    ).exists()
    new_status = (
        StudyPlan.Status.COMPLETED
        if is_complete
        else StudyPlan.Status.ACTIVE
    )
    if plan.status != new_status:
        plan.status = new_status
        plan.save(update_fields=["status", "updated_at"])
    return plan


@transaction.atomic
def toggle_recommendation_completion(*, recommendation, now=None):
    locked_recommendation = StudyRecommendation.objects.select_for_update().get(
        pk=recommendation.pk
    )
    locked_recommendation.completed_at = (
        None if locked_recommendation.completed_at else (now or timezone.now())
    )
    locked_recommendation.save(update_fields=["completed_at"])
    sync_plan_status(plan=locked_recommendation.plan)
    return locked_recommendation


@transaction.atomic
def start_study_session(*, plan, now=None):
    active_session = plan.sessions.filter(ended_at__isnull=True).first()
    if active_session is not None:
        return active_session, False
    session = StudySession.objects.create(
        plan=plan,
        started_at=now or timezone.now(),
    )
    return session, True


@transaction.atomic
def finish_study_session(*, session, now=None):
    locked_session = StudySession.objects.select_for_update().get(pk=session.pk)
    if locked_session.ended_at is not None:
        return locked_session
    locked_session.ended_at = now or timezone.now()
    locked_session.completed_recommendation_count = (
        locked_session.plan.recommendations.filter(
            completed_at__isnull=False
        ).count()
    )
    locked_session.save(
        update_fields=[
            "ended_at",
            "completed_recommendation_count",
        ]
    )
    sync_plan_status(plan=locked_session.plan)
    return locked_session
