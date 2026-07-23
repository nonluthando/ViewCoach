import pytest


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user(
        email="reviewer@example.com",
        password="test-password-123",
    )


@pytest.fixture
def other_user(db, django_user_model):
    return django_user_model.objects.create_user(
        email="other-reviewer@example.com",
        password="test-password-123",
    )
