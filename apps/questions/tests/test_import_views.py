from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.questions.models import (
    BehaviouralQuestion,
    Question,
    QuestionImportBatch,
    TechnicalQuestion,
)

pytestmark = pytest.mark.django_db


def _review_payload(batch, *, first_title=None, first_type=None):
    items = list(batch.items.order_by("position"))
    payload = {
        "form-TOTAL_FORMS": str(len(items)),
        "form-INITIAL_FORMS": str(len(items)),
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
    }
    for index, item in enumerate(items):
        payload[f"form-{index}-id"] = str(item.pk)
        payload[f"form-{index}-generated_title"] = (
            first_title if index == 0 and first_title else item.generated_title
        )
        payload[f"form-{index}-question_text"] = item.question_text
        payload[f"form-{index}-question_type"] = (
            first_type if index == 0 and first_type else item.question_type
        )
        if item.is_included:
            payload[f"form-{index}-is_included"] = "on"
    return payload


def test_import_start_requires_login(client):
    response = client.get(reverse("questions:import_start"))

    assert response.status_code == 302


def test_user_can_create_resumable_batch_from_pasted_questions(client, user):
    client.force_login(user)

    response = client.post(
        reverse("questions:import_start"),
        {
            "default_question_type": Question.Type.TECHNICAL,
            "paste_text": "1. Explain Two Sum\n2. Explain Binary Search",
        },
    )

    batch = QuestionImportBatch.objects.get(owner=user)
    assert response.status_code == 302
    assert response.url == reverse("questions:import_batch", args=[batch.pk])
    assert batch.status == QuestionImportBatch.Status.READY_FOR_REVIEW
    assert batch.items.count() == 2


def test_review_can_edit_title_and_override_individual_type(client, user):
    client.force_login(user)
    client.post(
        reverse("questions:import_start"),
        {
            "default_question_type": Question.Type.TECHNICAL,
            "paste_text": "1. Explain Two Sum\n2. Tell me about a conflict",
        },
    )
    batch = QuestionImportBatch.objects.get(owner=user)

    response = client.post(
        reverse("questions:import_batch", args=[batch.pk]),
        _review_payload(
            batch,
            first_title="Two Sum",
            first_type=Question.Type.BEHAVIOURAL,
        ),
    )

    first_item = batch.items.order_by("position").first()
    assert response.status_code == 302
    assert first_item.generated_title == "Two Sum"
    assert first_item.question_type == Question.Type.BEHAVIOURAL


def test_confirm_creates_questions_as_needs_notes_and_deletes_preview_items(client, user):
    client.force_login(user)
    client.post(
        reverse("questions:import_start"),
        {
            "default_question_type": Question.Type.TECHNICAL,
            "paste_text": "1. Explain Two Sum\n2. Explain Binary Search",
        },
    )
    batch = QuestionImportBatch.objects.get(owner=user)

    response = client.post(
        reverse("questions:import_confirm", args=[batch.pk]),
        {"confirmation_token": str(batch.idempotency_key)},
    )

    batch.refresh_from_db()
    assert response.status_code == 302
    assert batch.status == QuestionImportBatch.Status.IMPORTED
    assert batch.created_question_count == 2
    assert batch.items.count() == 0
    assert batch.source_text == ""
    assert TechnicalQuestion.objects.filter(owner=user).count() == 2
    assert set(Question.objects.values_list("status", flat=True)) == {Question.Status.NEEDS_NOTES}


def test_repeated_confirmation_creates_questions_only_once(client, user):
    client.force_login(user)
    client.post(
        reverse("questions:import_start"),
        {
            "default_question_type": Question.Type.TECHNICAL,
            "paste_text": "1. Explain Two Sum\n2. Explain Binary Search",
        },
    )
    batch = QuestionImportBatch.objects.get(owner=user)
    url = reverse("questions:import_confirm", args=[batch.pk])
    payload = {"confirmation_token": str(batch.idempotency_key)}

    first_response = client.post(url, payload)
    second_response = client.post(url, payload)

    assert first_response.status_code == 302
    assert second_response.status_code == 302
    assert Question.objects.filter(owner=user).count() == 2


def test_uploaded_file_is_deleted_after_questions_are_created(
    client, user, tmp_path, settings, django_capture_on_commit_callbacks
):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(user)
    upload = SimpleUploadedFile(
        "questions.txt",
        b"1. Explain Two Sum\n2. Explain Binary Search",
        content_type="text/plain",
    )

    client.post(
        reverse("questions:import_start"),
        {
            "default_question_type": Question.Type.TECHNICAL,
            "upload": upload,
        },
    )
    batch = QuestionImportBatch.objects.get(owner=user)
    file_path = Path(batch.temporary_file.path)
    assert file_path.exists()

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            reverse("questions:import_confirm", args=[batch.pk]),
            {"confirmation_token": str(batch.idempotency_key)},
        )

    batch.refresh_from_db()
    assert batch.temporary_file.name == ""
    assert not file_path.exists()


def test_questions_from_import_appear_in_library_with_needs_notes_status(client, user):
    client.force_login(user)
    client.post(
        reverse("questions:import_start"),
        {
            "default_question_type": Question.Type.BEHAVIOURAL,
            "paste_text": "Tell me about a conflict",
        },
    )
    batch = QuestionImportBatch.objects.get(owner=user)
    client.post(
        reverse("questions:import_confirm", args=[batch.pk]),
        {"confirmation_token": str(batch.idempotency_key)},
    )

    response = client.get(
        reverse("questions:list"),
        {"status": Question.Status.NEEDS_NOTES},
    )

    assert response.status_code == 200
    assert "Tell me about a conflict" in response.content.decode()
    assert BehaviouralQuestion.objects.filter(owner=user).exists()


def test_user_cannot_access_another_users_import_batch(client, other_user, user):
    batch = QuestionImportBatch.objects.create(
        owner=user,
        source_type=QuestionImportBatch.SourceType.PASTE,
        default_question_type=Question.Type.TECHNICAL,
    )
    client.force_login(other_user)

    response = client.get(reverse("questions:import_batch", args=[batch.pk]))

    assert response.status_code == 404


def test_unfinished_batch_can_be_deleted(client, user):
    batch = QuestionImportBatch.objects.create(
        owner=user,
        source_type=QuestionImportBatch.SourceType.PASTE,
        default_question_type=Question.Type.TECHNICAL,
        source_text="Explain Two Sum",
    )
    client.force_login(user)

    response = client.post(reverse("questions:import_delete", args=[batch.pk]))

    assert response.status_code == 302
    assert not QuestionImportBatch.objects.filter(pk=batch.pk).exists()


def test_imported_batch_is_archived_instead_of_deleted(client, user):
    batch = QuestionImportBatch.objects.create(
        owner=user,
        source_type=QuestionImportBatch.SourceType.PASTE,
        default_question_type=Question.Type.TECHNICAL,
        status=QuestionImportBatch.Status.IMPORTED,
        created_question_count=1,
    )
    client.force_login(user)

    delete_response = client.post(reverse("questions:import_delete", args=[batch.pk]))
    archive_response = client.post(reverse("questions:import_archive", args=[batch.pk]))

    batch.refresh_from_db()
    assert delete_response.status_code == 302
    assert archive_response.status_code == 302
    assert batch.status == QuestionImportBatch.Status.ARCHIVED
    assert batch.archived_at is not None


def test_confirm_from_review_saves_latest_edits_before_creating_questions(client, user):
    client.force_login(user)
    client.post(
        reverse("questions:import_start"),
        {
            "default_question_type": Question.Type.TECHNICAL,
            "paste_text": "Tell me about a conflict",
        },
    )
    batch = QuestionImportBatch.objects.get(owner=user)
    payload = _review_payload(
        batch,
        first_title="Conflict story",
        first_type=Question.Type.BEHAVIOURAL,
    )
    payload["action"] = "confirm"
    payload["confirmation_token"] = str(batch.idempotency_key)

    response = client.post(reverse("questions:import_batch", args=[batch.pk]), payload)

    batch.refresh_from_db()
    created = BehaviouralQuestion.objects.get(owner=user)
    assert response.status_code == 302
    assert batch.status == QuestionImportBatch.Status.IMPORTED
    assert created.title == "Conflict story"
    assert created.prompt == "Tell me about a conflict"


def test_deleting_user_with_imported_questions_does_not_raise(user):
    batch = QuestionImportBatch.objects.create(
        owner=user,
        source_type=QuestionImportBatch.SourceType.PASTE,
        default_question_type=Question.Type.TECHNICAL,
        status=QuestionImportBatch.Status.IMPORTED,
    )
    TechnicalQuestion.objects.create(
        owner=user,
        import_batch=batch,
        title="Two Sum",
        prompt="Explain Two Sum",
    )

    user.delete()

    assert not QuestionImportBatch.objects.filter(pk=batch.pk).exists()
    assert not Question.objects.filter(title="Two Sum").exists()


def test_import_review_and_history_pages_render(client, user):
    batch = QuestionImportBatch.objects.create(
        owner=user,
        source_type=QuestionImportBatch.SourceType.PASTE,
        default_question_type=Question.Type.TECHNICAL,
        status=QuestionImportBatch.Status.READY_FOR_REVIEW,
        source_text="Explain Two Sum",
    )
    batch.items.create(
        position=1,
        generated_title="Explain Two Sum",
        question_text="Explain Two Sum",
        normalized_text="explain two sum",
        question_type=Question.Type.TECHNICAL,
    )
    client.force_login(user)

    batch_response = client.get(reverse("questions:import_batch", args=[batch.pk]))
    history_response = client.get(reverse("questions:import_history"))

    assert batch_response.status_code == 200
    assert "Create questions" in batch_response.content.decode()
    assert history_response.status_code == 200
    assert "Pasted question list" in history_response.content.decode()
