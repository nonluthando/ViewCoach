from django.urls import path

from . import portfolio_views, views

urlpatterns = [
    path("", views.landing_page, name="home"),
    path("project/", portfolio_views.project_showcase, name="project_showcase"),
    path(
        "project/demo/",
        portfolio_views.portfolio_demo_guide,
        name="portfolio_demo_guide",
    ),
    path(
        "project/demo/start/",
        portfolio_views.portfolio_demo_start,
        name="portfolio_demo_start",
    ),
    path(
        "project/demo/reset/",
        portfolio_views.portfolio_demo_reset,
        name="portfolio_demo_reset",
    ),
    path(
        "project/demo/end/",
        portfolio_views.portfolio_demo_end,
        name="portfolio_demo_end",
    ),
    path(
        "project/demo/step/<slug:step_key>/",
        portfolio_views.portfolio_demo_step,
        name="portfolio_demo_step",
    ),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("learn/", views.learn, name="learn"),
    path("prepare/", views.prepare, name="prepare"),
    path("interview/", views.interview, name="interview"),
    path("health/", views.health_check, name="health"),
]
