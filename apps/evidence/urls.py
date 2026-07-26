from django.urls import path

from . import views

app_name = "evidence"

urlpatterns = [
    path("", views.evidence_list, name="list"),
    path("new/", views.evidence_create, name="create"),
    path(
        "interview-pack/",
        views.interview_pack,
        name="interview_pack",
    ),
    path(
        "projects/<int:evidence_id>/explanation/",
        views.project_explanation_edit,
        name="project_explanation_edit",
    ),
    path(
        "ai-coding-prep/",
        views.ai_coding_prep,
        name="ai_coding_prep",
    ),
    path(
        "ai-coding-prep/<slug:question_key>/answer/",
        views.ai_prep_answer_save,
        name="ai_prep_answer_save",
    ),
    path("<int:evidence_id>/", views.evidence_detail, name="detail"),
    path("<int:evidence_id>/edit/", views.evidence_edit, name="edit"),
    path("<int:evidence_id>/delete/", views.evidence_delete, name="delete"),
    path(
        "<int:evidence_id>/decisions/",
        views.decision_add,
        name="decision_add",
    ),
    path(
        "<int:evidence_id>/decisions/<int:decision_id>/delete/",
        views.decision_delete,
        name="decision_delete",
    ),
    path(
        "<int:evidence_id>/stories/",
        views.story_add,
        name="story_add",
    ),
    path(
        "<int:evidence_id>/stories/<int:story_id>/delete/",
        views.story_delete,
        name="story_delete",
    ),
    path(
        "topics/<int:topic_id>/profile/",
        views.topic_profile_save,
        name="topic_profile_save",
    ),
    path(
        "topics/<int:topic_id>/links/",
        views.topic_evidence_link,
        name="topic_link",
    ),
    path(
        "topics/<int:topic_id>/links/<int:link_id>/delete/",
        views.topic_evidence_unlink,
        name="topic_unlink",
    ),
    path(
        "questions/<int:question_id>/links/",
        views.question_evidence_link,
        name="question_link",
    ),
    path(
        "questions/<int:question_id>/links/<int:link_id>/delete/",
        views.question_evidence_unlink,
        name="question_unlink",
    ),
    path(
        "goals/<int:goal_id>/links/",
        views.goal_evidence_link,
        name="goal_link",
    ),
    path(
        "goals/<int:goal_id>/links/<int:link_id>/delete/",
        views.goal_evidence_unlink,
        name="goal_unlink",
    ),
]
