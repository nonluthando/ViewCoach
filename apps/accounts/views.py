from django.contrib.auth import login
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import AccountCreationForm


class SignUpView(UserPassesTestMixin, CreateView):
    form_class = AccountCreationForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("dashboard")

    def test_func(self):
        return self.request.user.is_anonymous

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response
