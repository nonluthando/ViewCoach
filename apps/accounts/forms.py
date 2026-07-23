from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm

from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    def clean_username(self):
        email = self.cleaned_data["username"]
        return email.strip().lower()


class AccountCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email


class AccountChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        duplicate_exists = (
            User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists()
        )
        if duplicate_exists:
            raise forms.ValidationError("An account with this email address already exists.")
        return email
