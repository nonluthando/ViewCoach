import pytest
from django.urls import reverse

from apps.evidence.models import BehaviouralStory

pytestmark = pytest.mark.django_db


def _story(evidence, **overrides):
    values = {
        "title": "Recovered a failing release",
        "situation": "A deployment failed before a deadline.",
        "task": "Restore the release without losing recent work.",
        "actions": "I traced the configuration mismatch and repaired the release.",
        "result": "The release passed its checks and shipped.",
        "reflection": "I now validate deployment configuration earlier.",
        "competencies": "Ownership, Problem solving",
        "follow_up_questions": "How did you isolate the failure?",
    }
    values.update(overrides)
    return BehaviouralStory.objects.create(evidence=evidence, **values)


def test_behavioural_story_readiness_tracks_missing_sections(evidence_item):
    story = _story(
        evidence_item,
        result="",
        follow_up_questions="",
    )

    assert story.completed_interview_sections == 4
    assert story.total_interview_sections == 6
    assert story.is_interview_ready is False
    assert story.missing_interview_sections == ["Result", "Follow-up questions"]


def test_behavioural_story_bank_requires_authentication(client):
    response = client.get(reverse("evidence:behavioural_story_bank"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_behavioural_story_bank_shows_progress_and_hides_other_users_stories(
    client,
    user,
    evidence_item,
    other_evidence,
):
    _story(evidence_item)
    _story(
        other_evidence,
        title="Private employer conflict",
        competencies="Conflict",
    )
    client.force_login(user)

    response = client.get(reverse("evidence:behavioural_story_bank"))
    html = response.content.decode()

    assert response.status_code == 200
    assert "Behavioural story bank" in html
    assert "Recovered a failing release" in html
    assert "Private employer conflict" not in html
    assert "2 of 8" in html
    assert "Interview ready" in html
    assert "Tell me about a time you took ownership" in html


def test_user_can_create_story_from_story_bank(client, user, evidence_item):
    client.force_login(user)

    response = client.post(
        reverse("evidence:behavioural_story_create"),
        {
            "evidence": evidence_item.pk,
            "title": "Learned Django quickly",
            "situation": "The project stack changed.",
            "task": "Become productive in the new stack.",
            "actions": "I traced an existing feature and built a small vertical slice.",
            "result": "I delivered the assigned feature.",
            "reflection": "A working slice exposes gaps faster than passive reading.",
            "competencies": "Learning, Adaptability",
            "follow_up_questions": "What did you find hardest?",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("evidence:behavioural_story_bank")
    assert BehaviouralStory.objects.filter(
        evidence=evidence_item,
        title="Learned Django quickly",
    ).exists()


def test_story_bank_form_rejects_another_users_evidence(
    client,
    user,
    other_evidence,
):
    client.force_login(user)

    response = client.post(
        reverse("evidence:behavioural_story_create"),
        {
            "evidence": other_evidence.pk,
            "title": "Unsupported private story",
            "situation": "Private.",
            "task": "Private.",
            "actions": "Private.",
            "result": "Private.",
            "reflection": "Private.",
            "competencies": "Ownership",
            "follow_up_questions": "Private?",
        },
    )

    assert response.status_code == 200
    assert BehaviouralStory.objects.filter(title="Unsupported private story").exists() is False


def test_user_can_edit_their_story_but_not_another_users(
    client,
    user,
    evidence_item,
    other_evidence,
):
    story = _story(evidence_item)
    private_story = _story(other_evidence, title="Private story")
    client.force_login(user)

    response = client.post(
        reverse("evidence:behavioural_story_edit", args=[story.pk]),
        {
            "evidence": evidence_item.pk,
            "title": "Recovered a production release",
            "situation": story.situation,
            "task": story.task,
            "actions": story.actions,
            "result": story.result,
            "reflection": story.reflection,
            "competencies": story.competencies,
            "follow_up_questions": story.follow_up_questions,
        },
    )
    private_response = client.get(
        reverse("evidence:behavioural_story_edit", args=[private_story.pk])
    )

    story.refresh_from_db()
    assert response.status_code == 302
    assert story.title == "Recovered a production release"
    assert private_response.status_code == 404


def test_story_bank_can_filter_by_competency(client, user, evidence_item):
    _story(evidence_item, title="Owned the release", competencies="Ownership")
    _story(
        evidence_item,
        title="Resolved a disagreement",
        competencies="Conflict, Communication",
    )
    client.force_login(user)

    response = client.get(
        reverse("evidence:behavioural_story_bank"),
        {"competency": "conflict"},
    )
    html = response.content.decode()

    assert response.status_code == 200
    assert "Resolved a disagreement" in html
    assert "Owned the release" not in html
