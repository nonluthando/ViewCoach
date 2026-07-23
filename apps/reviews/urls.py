from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("", views.review_queue, name="queue"),
    path("history/", views.review_history, name="history"),
    path("<int:pk>/", views.review_question, name="review"),
    path("<int:pk>/rate/", views.submit_review, name="submit"),
]
