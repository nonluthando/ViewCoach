from django.contrib.auth.decorators import login_required
from django.db import OperationalError, connection
from django.http import JsonResponse
from django.shortcuts import render

from .dashboard_services import build_dashboard_context


def landing_page(request):
    return render(request, "core/landing_page.html")


@login_required
def dashboard(request):
    context = build_dashboard_context(
        user=request.user,
        month_value=request.GET.get("month", ""),
    )
    return render(request, "core/dashboard.html", context)


@login_required
def learn(request):
    return render(request, "core/learn.html")


@login_required
def prepare(request):
    return render(request, "core/prepare.html")


@login_required
def interview(request):
    return render(request, "core/interview.html")


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError:
        return JsonResponse({"status": "unavailable"}, status=503)

    return JsonResponse({"status": "ok"})
