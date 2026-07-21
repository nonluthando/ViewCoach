from django.urls import path

from . import views

app_name = "questions"

urlpatterns = [
    path("", views.question_list, name="list"),
    path("new/", views.choose_question_type, name="choose_type"),
    path("new/<slug:question_type_slug>/", views.question_create, name="create"),
    path("<int:pk>/", views.question_detail, name="detail"),
    path("<int:pk>/edit/", views.question_edit, name="edit"),
    path("<int:pk>/delete/", views.question_delete, name="delete"),
]
