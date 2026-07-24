from django.urls import path

from . import views

app_name = "goals"

urlpatterns = [
    path("", views.goal_list, name="list"),
    path("new/", views.goal_create, name="create"),
    path("<int:goal_id>/", views.goal_detail, name="detail"),
    path("<int:goal_id>/edit/", views.goal_edit, name="edit"),
    path("<int:goal_id>/primary/", views.goal_set_primary, name="set_primary"),
    path("<int:goal_id>/status/", views.goal_update_status, name="update_status"),
    path("<int:goal_id>/stages/", views.stage_add, name="stage_add"),
    path(
        "<int:goal_id>/stages/<int:stage_id>/current/",
        views.stage_set_current,
        name="stage_set_current",
    ),
    path(
        "<int:goal_id>/stages/<int:stage_id>/complete/",
        views.stage_complete,
        name="stage_complete",
    ),
]
