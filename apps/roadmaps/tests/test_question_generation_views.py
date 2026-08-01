import pytest
from django.urls import reverse

from apps.questions.models import ConceptQuestion, Question, QuestionGenerationBatch
from apps.roadmaps.models import Roadmap, RoadmapSection, RoadmapTopic, UserTopicProgress

pytestmark = pytest.mark.django_db


def _topic():
    roadmap = Roadmap.objects.create(
        title="Python",
        slug="question-generation-view-python",
        kind=Roadmap.Kind.SKILL,
    )
    section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="Foundations",
        slug="foundations",
        position=1,
    )
    topic = RoadmapTopic.objects.create(
        section=section,
        title="Python types",
        slug="python-types",
        position=1,
    )
    return roadmap, topic


def test_generate_view_requires_saved_notes(client, user):
    client.force_login(user)
    roadmap, topic = _topic()
    response = client.post(
        reverse(
            "roadmaps:generate_topic_questions",
            kwargs={"slug": roadmap.slug, "topic_id": topic.pk},
        ),
        {"count": 3},
        follow=True,
    )
    assert response.status_code == 200
    assert b"Save topic notes before generating" in response.content
    assert not QuestionGenerationBatch.objects.exists()


def test_generate_view_redirects_to_editable_draft_preview(client, user, monkeypatch):
    client.force_login(user)
    roadmap, topic = _topic()
    notes = (
        "Python is dynamically typed. Variables may refer to values of different "
        "types, while operations still follow compatibility rules. This provides "
        "the source material for a grounded concept question."
    )
    UserTopicProgress.objects.create(user=user, topic=topic, notes=notes)

    def fake_generate_topic_question_drafts(*, user, topic, notes, count):
        batch = QuestionGenerationBatch.objects.create(
            user=user,
            topic=topic,
            notes_snapshot=notes,
            requested_count=count,
            status=QuestionGenerationBatch.Status.READY,
            generation_model="fake",
            created_question_count=1,
        )
        ConceptQuestion.objects.create(
            owner=user,
            title="Dynamic typing",
            prompt="What does dynamically typed mean?",
            category=ConceptQuestion.Category.PYTHON,
            canonical_answer="Variables may refer to values of different types.",
            status=Question.Status.NEEDS_NOTES,
            generation_batch=batch,
            source_topic=topic,
        )
        return batch

    monkeypatch.setattr(
        "apps.roadmaps.views.generate_topic_question_drafts",
        fake_generate_topic_question_drafts,
    )
    response = client.post(
        reverse(
            "roadmaps:generate_topic_questions",
            kwargs={"slug": roadmap.slug, "topic_id": topic.pk},
        ),
        {"count": 3},
    )
    batch = QuestionGenerationBatch.objects.get()
    assert response.status_code == 302
    assert response.url == reverse(
        "roadmaps:topic_question_drafts",
        kwargs={
            "slug": roadmap.slug,
            "topic_id": topic.pk,
            "batch_id": batch.pk,
        },
    )
