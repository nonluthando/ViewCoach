from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    class NeedType(models.TextChoices):
        LEARN_ORGANISE = (
            "LEARN_ORGANISE",
            "Learn new concepts and organise learning materials",
        )
        PRACTISE_RETAIN = (
            "PRACTISE_RETAIN",
            "Practise and retain knowledge with cards and reviews",
        )
        INTERVIEW_SKILLS = (
            "INTERVIEW_SKILLS",
            "Build interview skills with stories, evidence and mocks",
        )

    username = None
    email = models.EmailField(unique=True)
    primary_need_type = models.CharField(
        max_length=24,
        choices=NeedType.choices,
        blank=True,
        default="",
    )
    secondary_need_type = models.CharField(
        max_length=24,
        choices=NeedType.choices,
        blank=True,
        default="",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email).lower()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.email
