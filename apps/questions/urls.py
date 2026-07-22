from django.urls import path

from . import views

app_name = "questions"

urlpatterns = [
    path("", views.question_list, name="list"),
    path("bulk/save-built-in/", views.bulk_save_built_in, name="bulk_save_built_in"),
    path("bulk/mark-ready/", views.bulk_mark_ready, name="bulk_mark_ready"),
    path("new/", views.choose_question_type, name="choose_type"),
    path("new/<slug:question_type_slug>/", views.question_create, name="create"),
    path("import/", views.question_import_start, name="import_start"),
    path("import/history/", views.question_import_history, name="import_history"),
    path("import/<int:batch_id>/", views.question_import_batch, name="import_batch"),
    path(
        "import/<int:batch_id>/confirm/",
        views.question_import_confirm,
        name="import_confirm",
    ),
    path(
        "import/<int:batch_id>/delete/",
        views.question_import_delete,
        name="import_delete",
    ),
    path(
        "import/<int:batch_id>/archive/",
        views.question_import_archive,
        name="import_archive",
    ),
    path("<int:pk>/", views.question_detail, name="detail"),
    path("<int:pk>/edit/", views.question_edit, name="edit"),
    path("<int:pk>/notes/", views.question_notes, name="notes"),
    path("<int:pk>/bookmark/", views.question_toggle_bookmark, name="toggle_bookmark"),
    path("<int:pk>/mark-ready/", views.question_mark_ready, name="mark_ready"),
    path("<int:pk>/delete/", views.question_delete, name="delete"),
]
