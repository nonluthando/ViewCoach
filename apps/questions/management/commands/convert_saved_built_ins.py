from django.core.management.base import BaseCommand

from apps.questions.models import UserQuestionState
from apps.questions.services import copy_built_in_question_for_user


class Command(BaseCommand):
    help = "Convert legacy saved built-in questions into owned user copies."

    def handle(self, *args, **options):
        saved_states = list(
            UserQuestionState.objects.select_related("user", "question").filter(
                bookmarked=True,
                question__is_system=True,
            )
        )

        created_count = 0
        existing_count = 0
        for state in saved_states:
            _, created = copy_built_in_question_for_user(
                question=state.question,
                user=state.user,
            )
            if created:
                created_count += 1
            else:
                existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created_count} user copies; "
                f"{existing_count} already existed."
            )
        )
