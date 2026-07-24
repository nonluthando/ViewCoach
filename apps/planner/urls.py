from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("", views.today_plan, name="today"),
    path("regenerate/", views.regenerate_plan, name="regenerate"),
    path(
        "recommendations/<int:recommendation_id>/toggle/",
        views.toggle_recommendation,
        name="toggle_recommendation",
    ),
    path("sessions/start/", views.start_session, name="start_session"),
    path("sessions/finish/", views.finish_session, name="finish_session"),
]
