from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone

from .portfolio_demo import delete_portfolio_demo_user, is_portfolio_demo_user

BLOCKED_DEMO_POST_VIEWS = {
    "knowledge:help_assistant",
    "questions:import_confirm",
    "questions:import_start",
    "roadmaps:generate_topic_questions",
    "roadmaps:ibm_course_confirm",
    "roadmaps:ibm_course_import",
    "roadmaps:youtube_import",
    "roadmaps:youtube_import_confirm",
}


class PortfolioDemoMiddleware:
    """Apply expiry and cost-safety rules to temporary demo accounts."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if is_portfolio_demo_user(request.user):
            cutoff = timezone.now() - timedelta(
                hours=settings.PORTFOLIO_DEMO_TTL_HOURS
            )
            if request.user.date_joined < cutoff:
                user_id = request.user.pk
                logout(request)
                delete_portfolio_demo_user(user_id=user_id)
                messages.info(
                    request,
                    "That temporary demo expired. Start a fresh workspace to continue.",
                )
                return redirect("project_showcase")

        response = self.get_response(request)
        if is_portfolio_demo_user(request.user):
            response["Cache-Control"] = "private, no-store, max-age=0"
            response["Pragma"] = "no-cache"
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if (
            is_portfolio_demo_user(request.user)
            and request.method == "POST"
            and request.resolver_match
            and request.resolver_match.view_name in BLOCKED_DEMO_POST_VIEWS
        ):
            messages.warning(
                request,
                (
                    "External imports and AI generation are disabled in the public "
                    "demo. The seeded examples remain fully available to inspect."
                ),
            )
            return redirect("portfolio_demo_guide")
        return None
