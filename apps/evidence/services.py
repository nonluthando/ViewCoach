from django.db.models import Count, Q

from .models import EvidenceItem, TopicEvidenceProfile


def evidence_library_queryset(*, user):
    return EvidenceItem.objects.filter(owner=user).annotate(
        decision_count=Count("decisions", distinct=True),
        story_count=Count("behavioural_stories", distinct=True),
        topic_count=Count("topic_links", distinct=True),
        question_count=Count("question_links", distinct=True),
        goal_count=Count("goal_links", distinct=True),
    )


def filter_evidence_library(*, user, search_term="", source_type=""):
    evidence = evidence_library_queryset(user=user)
    if search_term:
        evidence = evidence.filter(
            Q(title__icontains=search_term)
            | Q(organisation__icontains=search_term)
            | Q(role_or_context__icontains=search_term)
            | Q(summary__icontains=search_term)
            | Q(problem__icontains=search_term)
            | Q(personal_contribution__icontains=search_term)
            | Q(technologies__icontains=search_term)
            | Q(outcomes__icontains=search_term)
        )
    valid_types = {value for value, _ in EvidenceItem.SourceType.choices}
    if source_type in valid_types:
        evidence = evidence.filter(source_type=source_type)
    return evidence


def evidence_dashboard_summary(*, user):
    items = EvidenceItem.objects.filter(owner=user)
    topic_profiles = TopicEvidenceProfile.objects.filter(user=user)
    return {
        "total_count": items.count(),
        "project_count": items.filter(source_type=EvidenceItem.SourceType.PROJECT).count(),
        "work_count": items.filter(source_type=EvidenceItem.SourceType.WORK).count(),
        "interview_ready_topic_count": topic_profiles.filter(
            readiness=TopicEvidenceProfile.Readiness.INTERVIEW_READY
        ).count(),
    }
