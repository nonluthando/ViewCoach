from django.urls import path

from . import views, youtube_views

app_name = "roadmaps"

urlpatterns = [
    path("", views.roadmap_list, name="list"),
    path(
        "youtube/import/",
        youtube_views.youtube_playlist_import,
        name="youtube_import",
    ),
    path(
        "youtube/import/confirm/",
        youtube_views.youtube_playlist_confirm,
        name="youtube_import_confirm",
    ),
    path(
        "<slug:slug>/youtube/delete/",
        youtube_views.delete_youtube_roadmap,
        name="delete_youtube_roadmap",
    ),
    path("<slug:slug>/", views.roadmap_detail, name="detail"),
    path("<slug:slug>/start/", views.start_roadmap, name="start"),
    path(
        "<slug:slug>/topics/<int:topic_id>/",
        views.topic_detail,
        name="topic_detail",
    ),
    path(
        "<slug:slug>/topics/<int:topic_id>/status/",
        views.update_topic_status,
        name="update_topic_status",
    ),
    path(
        "<slug:slug>/topics/<int:topic_id>/notes/",
        views.save_topic_notes,
        name="save_topic_notes",
    ),
    path(
        "<slug:slug>/topics/<int:topic_id>/resources/",
        views.add_topic_resource,
        name="add_topic_resource",
    ),
    path(
        (
            "<slug:slug>/topics/<int:topic_id>/resources/"
            "<int:resource_id>/delete/"
        ),
        views.delete_topic_resource,
        name="delete_topic_resource",
    ),
    path(
        "<slug:slug>/topics/<int:topic_id>/youtube/complete/",
        youtube_views.complete_youtube_video,
        name="complete_youtube_video",
    ),
]
