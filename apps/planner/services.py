from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.goals.models import InterviewGoal
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
            enrolment_query = enrolment_query.filter(
                roadmap_id__in=linked_roadmap_ids
            )

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
        if completed_counts.get(enrolment.roadmap_id, 0)
        < topic_counts.get(enrolment.roadmap_id, 0)
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


def _active_roadmap_enrolment(*, user, goal=None):
    enrolments = _ordered_active_roadmap_enrolments(user=user, goal=goal)
    return enrolments[0] if enrolments else None


def _unfinished_roadmap_topics(*, user, enrolment, excluded_topic_ids=None):
    excluded_topic_ids = excluded_topic_ids or set()
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
    available = topics.exclude(
        pk__in=completed_topic_ids
    ).exclude(pk__in=excluded_topic_ids)

    in_progress_ids = set(
        UserTopicProgress.objects.filter(
            user=user,
            status=UserTopicProgress.Status.IN_PROGRESS,
            topic__section__roadmap=enrolment.roadmap,
        ).values_list("topic_id", flat=True)
    )
    return sorted(
        available.order_by(*topic_ordering),
        key=lambda topic: (0 if topic.pk in in_progress_ids else 1),
    )


def _next_roadmap_topic(*, user, enrolment, excluded_topic_ids=None):
    topics = _unfinished_roadmap_topics(
        user=user,
        enrolment=enrolment,
        excluded_topic_ids=excluded_topic_ids,
    )
    return topics[0] if topics else None


def _ordered_roadmap_topics(*, user, enrolments, limit):
    topic_queues = [
        _unfinished_roadmap_topics(user=user, enrolment=enrolment)
        for enrolment in enrolments
    ]
    selected = []
    while len(selected) < limit:
        added_topic = False
        for queue in topic_queues:
            if not queue:
                continue
            selected.append(queue.pop(0))
            added_topic = True
            if len(selected) == limit:
                break
        if not added_topic:
            break
    return selected


def _recent_weak_questions(*, user, excluded_question_ids, now, limit=10):
    if limit <= 0:
        return []

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

    results = []
    seen_question_ids = set()
    for attempt in attempts[:100]:
        question = attempt.state.question
        if question.pk in seen_question_ids:
            continue
        seen_question_ids.add(question.pk)
        results.append((question, attempt))
        if len(results) == limit:
            break
    return results


def _recent_weak_question(*, user, excluded_question_ids, now):
    questions = _recent_weak_questions(
        user=user,
        excluded_question_ids=excluded_question_ids,
        now=now,
        limit=1,
    )
    return questions[0] if questions else (None, None)


def _practice_question(*, user, topic, excluded_question_ids, plan_date, goal=None):
    questions = TechnicalQuestion.objects.filter(is_system=True).exclude(
        pk__in=excluded_question_ids
    )

    topic_words = []
    if topic is not None:
        topic_words.extend(
            word.strip(".,:;()[]").lower()
            for word in topic.title.split()
            if len(word.strip(".,:;()[]")) >= 4
        )
    if goal is not None:
        topic_words.extend(
            word.strip(".,:;()[]").lower()
            for word in goal.role_title.replace("/", " ").replace("-", " ").split()
            if len(word.strip(".,:;()[]")) >= 4
        )

    if topic_words:
        topic_filter = Q()
        for word in dict.fromkeys(topic_words[:6]):
            topic_filter |= Q(title__icontains=word)
            topic_filter |= Q(topic__icontains=word)
            topic_filter |= Q(pattern__icontains=word)
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
    goal = _primary_goal(user=user)

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

    enrolments = _ordered_active_roadmap_enrolments(user=user, goal=goal)
    first_selected_topic = None
    if remaining_minutes >= 15 and enrolments:
        if time_budget_minutes <= 60:
            roadmap_allocation = min(ROADMAP_TOPIC_MINUTES, remaining_minutes)
        else:
            roadmap_allocation = min(
                remaining_minutes,
                max(ROADMAP_TOPIC_MINUTES, time_budget_minutes // 2),
            )
        roadmap_limit = min(12, max(1, roadmap_allocation // 15))
        roadmap_topics = _ordered_roadmap_topics(
            user=user,
            enrolments=enrolments,
            limit=roadmap_limit,
        )
        roadmap_minutes_left = roadmap_allocation

        for topic in roadmap_topics:
            if remaining_minutes < 15 or roadmap_minutes_left < 15:
                break
            estimated_minutes = min(
                ROADMAP_TOPIC_MINUTES,
                remaining_minutes,
                roadmap_minutes_left,
            )
            enrolment = next(
                item
                for item in enrolments
                if item.roadmap_id == topic.section.roadmap_id
            )
            deadline_note = ""
            priority_score = 80
            goal_deadline = goal.next_deadline if goal else None
            target_date = goal_deadline or enrolment.target_date
            if target_date:
                days_remaining = (target_date - plan_date).days
                if 0 <= days_remaining <= 14:
                    priority_score += 10
                    deadline_note = f" Your next stage is {days_remaining} days away."
            if goal is not None:
                deadline_note += f" This supports your primary goal: {goal.title}."

            payloads.append(
                {
                    "kind": StudyRecommendation.Kind.ROADMAP,
                    "title": f"Continue: {topic.title}",
                    "description": (
                        f"Move the {enrolment.roadmap.title} roadmap forward "
                        "with one focused topic."
                    ),
                    "rationale": (
                        "This is one of the next unfinished topics across your "
                        f"active roadmaps.{deadline_note}"
                    ),
                    "estimated_minutes": estimated_minutes,
                    "priority_score": priority_score,
                    "topic": topic,
                }
            )
            first_selected_topic = first_selected_topic or topic
            remaining_minutes -= estimated_minutes
            roadmap_minutes_left -= estimated_minutes

    weak_limit = min(10, remaining_minutes // WEAK_AREA_MINUTES)
    weak_questions = _recent_weak_questions(
        user=user,
        excluded_question_ids=selected_question_ids,
        now=now,
        limit=weak_limit,
    )
    for weak_question, weak_attempt in weak_questions:
        if remaining_minutes < WEAK_AREA_MINUTES:
            break
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

    practice_count = 0
    while remaining_minutes >= 15 and practice_count < 28:
        practice_question = _practice_question(
            user=user,
            topic=first_selected_topic,
            excluded_question_ids=selected_question_ids,
            plan_date=plan_date,
            goal=goal,
        )
        if practice_question is None:
            break
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
                    + (f" It is matched to {goal.title}." if goal else "")
                ),
                "estimated_minutes": estimated_minutes,
                "priority_score": 50,
                "question": practice_question,
            }
        )
        selected_question_ids.add(practice_question.pk)
        remaining_minutes -= estimated_minutes
        practice_count += 1

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
