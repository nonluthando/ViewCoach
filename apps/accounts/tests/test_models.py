import pytest

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_create_user_uses_email_as_identity():
    user = User.objects.create_user(email="Tee@Example.COM", password="safe-test-password")

    assert user.email == "tee@example.com"
    assert user.username is None
    assert user.check_password("safe-test-password")
    assert not user.is_staff
    assert not user.is_superuser


def test_create_user_requires_email():
    with pytest.raises(ValueError, match="email address is required"):
        User.objects.create_user(email="", password="safe-test-password")


def test_create_superuser_sets_required_flags():
    user = User.objects.create_superuser(
        email="admin@example.com",
        password="safe-test-password",
    )

    assert user.is_staff
    assert user.is_superuser
    assert user.is_active
