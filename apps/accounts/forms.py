from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserChangeForm, UserCreationForm

from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    def clean_username(self):
        email = self.cleaned_data["username"]
        return email.strip().lower()


class AccountCreationForm(UserCreationForm):
    primary_need_type = forms.ChoiceField(
        label="What are you mainly using ViewCoach for?",
        choices=User.NeedType.choices,
        widget=forms.RadioSelect,
    )
    secondary_need_type = forms.ChoiceField(
        label="Secondary aim",
        choices=[("", "No secondary aim")] + list(User.NeedType.choices),
        required=False,
        help_text="Optional. You can change this later in settings.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "primary_need_type",
            "secondary_need_type",
        )

    def clean(self):
        cleaned_data = super().clean()
        primary = cleaned_data.get("primary_need_type")
        secondary = cleaned_data.get("secondary_need_type")
        if primary and secondary and primary == secondary:
            self.add_error(
                "secondary_need_type",
                "Choose a different secondary aim or leave it empty.",
            )
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email


class NeedTypePreferencesForm(forms.ModelForm):
    primary_need_type = forms.ChoiceField(
        label="Primary aim",
        choices=User.NeedType.choices,
        widget=forms.RadioSelect,
    )
    secondary_need_type = forms.ChoiceField(
        label="Secondary aim",
        choices=[("", "No secondary aim")] + list(User.NeedType.choices),
        required=False,
    )

    class Meta:
        model = User
        fields = ("primary_need_type", "secondary_need_type")

    def clean(self):
        cleaned_data = super().clean()
        primary = cleaned_data.get("primary_need_type")
        secondary = cleaned_data.get("secondary_need_type")
        if primary and secondary and primary == secondary:
            self.add_error(
                "secondary_need_type",
                "Choose a different secondary aim or leave it empty.",
            )
        return cleaned_data


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
