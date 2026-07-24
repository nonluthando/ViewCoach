import pytest

from apps.accounts.models import User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="tee@example.com",
        password="safe-test-password",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="other@example.com",
        password="safe-test-password",
    )
