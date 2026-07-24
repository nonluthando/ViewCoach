from django.urls import path

from . import views

app_name = "interviews"

urlpatterns = [
    path("", views.interview_list, name="list"),
    path("new/", views.interview_create, name="create"),
    path("<int:interview_id>/", views.interview_session, name="session"),
    path(
        "<int:interview_id>/items/<int:item_id>/submit/",
        views.interview_submit,
        name="submit",
    ),
    path(
        "<int:interview_id>/summary/",
        views.interview_summary,
        name="summary",
    ),
    path(
        "<int:interview_id>/end/",
        views.interview_abandon,
        name="abandon",
    ),
]
