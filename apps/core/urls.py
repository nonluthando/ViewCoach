from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing_page, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("learn/", views.learn, name="learn"),
    path("prepare/", views.prepare, name="prepare"),
    path("interview/", views.interview, name="interview"),
    path("health/", views.health_check, name="health"),
]
