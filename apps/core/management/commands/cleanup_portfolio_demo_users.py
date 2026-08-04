from django.core.management.base import BaseCommand

from apps.core.portfolio_demo import (
    cleanup_expired_portfolio_demo_users,
    portfolio_demo_users,
)


class Command(BaseCommand):
    help = "Delete expired temporary recruiter-demo users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            dest="delete_all",
            help="Delete every temporary recruiter-demo user.",
        )

    def handle(self, *args, **options):
        if options["delete_all"]:
            users = portfolio_demo_users()
            count = users.count()
            users.delete()
        else:
            count = cleanup_expired_portfolio_demo_users()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} temporary portfolio demo "
                f"user{'s' if count != 1 else ''}."
            )
        )
