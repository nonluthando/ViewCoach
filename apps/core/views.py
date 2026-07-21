from django.contrib.auth.decorators import login_required
from django.db import OperationalError, connection
from django.http import JsonResponse
from django.shortcuts import render


def landing_page(request):
    return render(request, "core/landing_page.html")


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html")


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError:
        return JsonResponse({"status": "unavailable"}, status=503)

    return JsonResponse({"status": "ok"})
