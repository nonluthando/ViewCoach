from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("questions/", include("apps.questions.urls")),
    path("reviews/", include("apps.reviews.urls")),
    path("roadmaps/", include("apps.roadmaps.urls")),
]
