from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .forms import EmailAuthenticationForm
from .views import SignUpView, need_type_preferences

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path(
        "preferences/",
        need_type_preferences,
        name="need_type_preferences",
    ),
    path(
        "login/",
        LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=EmailAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
]
