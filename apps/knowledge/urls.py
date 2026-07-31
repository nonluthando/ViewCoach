from django.urls import path

from . import views

app_name = "knowledge"

urlpatterns = [
    path(
        "",
        views.help_assistant,
        name="help_assistant",
    ),
]
