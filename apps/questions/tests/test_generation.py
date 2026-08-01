import json

import pytest

from apps.questions.generation import generate_topic_question_drafts
from apps.questions.models import Question, QuestionGenerationBatch
from apps.roadmaps.models import Roadmap, RoadmapSection, RoadmapTopic

pytestmark = pytest.mark.django_db


class FakeProvider:
    model = "fake-question-model"

    def generate(self, *, topic_title, notes, count):
        assert topic_title == "Python types"
        assert "dynamically typed" in notes
        assert count == 3
        return json.dumps(
            {
                "questions": [
                    {
                        "question_type": "CONCEPT",
                        "title": "Dynamic typing",
                        "prompt": "What does dynamically typed mean in Python?",
                        "canonical_answer": "A variable can refer to values of different types.",
                        "key_points": [
                            "Variables are not permanently bound to one type.",
                            "Operations still follow compatibility rules.",
                        ],
                        "example": "",
                        "common_misconception": "Dynamic typing does not mean type rules disappear.",
                    },
                    {
                        "question_type": "TECHNICAL",
                        "title": "Boolean arithmetic",
                        "prompt": "Why does True + 4 evaluate to 5?",
                        "intuition": "True behaves like the integer value 1.",
                        "optimal_approach": "Explain that bool is a subclass of int in Python.",
                        "mistakes": "Do not claim that 4 is converted to a string.",
                    },
                ]
            }
        )


def _topic():
    roadmap = Roadmap.objects.create(
        title="Python",
        slug="question-generation-python",
        kind=Roadmap.Kind.SKILL,
    )
    section = RoadmapSection.objects.create(
        roadmap=roadmap,
        title="Foundations",
        slug="foundations",
        position=1,
    )
    return RoadmapTopic.objects.create(
        section=section,
        title="Python types",
        slug="python-types",
        position=1,
    )


def test_generate_topic_question_drafts_creates_editable_owned_questions(user):
    topic = _topic()
    notes = (
        "Python is dynamically typed, meaning a variable can refer to values of "
        "different types. Operations still obey compatibility rules. True + 4 "
        "equals 5 because bool is a subclass of int and True behaves like 1."
    )
    batch = generate_topic_question_drafts(
        user=user,
        topic=topic,
        notes=notes,
        count=3,
        provider=FakeProvider(),
    )
    assert batch.status == QuestionGenerationBatch.Status.READY
    assert batch.generation_model == "fake-question-model"
    assert batch.created_question_count == 2
    questions = list(batch.created_questions.order_by("pk"))
    assert {question.question_type for question in questions} == {
        Question.Type.CONCEPT,
        Question.Type.TECHNICAL,
    }
    assert all(question.owner == user for question in questions)
    assert all(question.source_topic == topic for question in questions)
    assert all(question.status == Question.Status.NEEDS_NOTES for question in questions)
    assert all(question.can_mark_ready for question in questions)


def test_generation_rejects_notes_that_are_too_short(user, settings):
    settings.QUESTION_GENERATION_MIN_NOTE_CHARACTERS = 80
    topic = _topic()
    with pytest.raises(ValueError, match="at least 80 characters"):
        generate_topic_question_drafts(
            user=user,
            topic=topic,
            notes="Too short.",
            count=3,
            provider=FakeProvider(),
        )
    assert not QuestionGenerationBatch.objects.exists()
