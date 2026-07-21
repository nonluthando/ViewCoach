from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing_page, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("health/", views.health_check, name="health"),
]
