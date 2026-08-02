from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import CreateView

from .forms import AccountCreationForm, NeedTypePreferencesForm
from .needs import need_type_experience


class SignUpView(UserPassesTestMixin, CreateView):
    form_class = AccountCreationForm
    template_name = "accounts/signup.html"

    def test_func(self):
        return self.request.user.is_anonymous

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

    def get_success_url(self):
        experience = need_type_experience(self.object.primary_need_type)
        if experience is None:
            return reverse("dashboard")
        return reverse(experience["route_name"])


@login_required
def need_type_preferences(request):
    form = NeedTypePreferencesForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "Your ViewCoach aims were updated. Future plans will use them.",
        )
        return redirect("dashboard")

    return render(
        request,
        "accounts/need_type_preferences.html",
        {"form": form},
    )
