import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_topic_workspace_surfaces_personal_evidence_section(client, user, topic):
    client.force_login(user)

    response = client.get(
        reverse(
            "roadmaps:topic_detail",
            kwargs={
                "slug": topic.section.roadmap.slug,
                "topic_id": topic.pk,
            },
        )
    )

    assert response.status_code == 200
    assert "Personal evidence and interview framing" in response.content.decode()


def test_question_detail_surfaces_real_example_section(
    client,
    user,
    technical_question,
):
    client.force_login(user)

    response = client.get(reverse("questions:detail", args=[technical_question.pk]))

    assert response.status_code == 200
    assert "Real examples for this answer" in response.content.decode()


def test_goal_detail_surfaces_goal_specific_evidence(client, user, goal):
    client.force_login(user)

    response = client.get(reverse("goals:detail", args=[goal.pk]))

    assert response.status_code == 200
    assert "Evidence for this goal" in response.content.decode()


def test_dashboard_counts_private_evidence(client, user, evidence_item):
    client.force_login(user)

    response = client.get(reverse("dashboard"))

    assert response.status_code == 200
    assert response.context["evidence_summary"]["total_count"] == 1
    assert reverse("evidence:list") in response.content.decode()
