from django.urls import path

from . import views

app_name = "roadmaps"

urlpatterns = [
    path("", views.roadmap_list, name="list"),
    path("<slug:slug>/", views.roadmap_detail, name="detail"),
    path("<slug:slug>/start/", views.start_roadmap, name="start"),
    path(
        "<slug:slug>/topics/<int:topic_id>/status/",
        views.update_topic_status,
        name="update_topic_status",
    ),
]
