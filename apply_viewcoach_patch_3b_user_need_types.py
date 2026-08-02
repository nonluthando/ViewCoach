#!/usr/bin/env python3
# ruff: noqa: E501
# Apply ViewCoach Patch 3B: user need types and aim-weighted planning.

from pathlib import Path

ROOT = Path.cwd()


def read(path):
    target = ROOT / path
    if not target.exists():
        raise SystemExit(f"Missing required file: {path}")
    return target.read_text()


def write(path, content):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def replace_once(path, old, new, label):
    text = read(path)
    if new in text:
        print(f"✓ Already applied: {label}")
        return
    if old not in text:
        raise SystemExit(f"Could not find marker for {label} in {path}")
    write(path, text.replace(old, new, 1))
    print(f"✓ Applied: {label}")


def create_once(path, content, label):
    target = ROOT / path
    if target.exists():
        if target.read_text() == content:
            print(f"✓ Already created: {label}")
            return
        raise SystemExit(f"Refusing to overwrite existing file: {path}")
    write(path, content)
    print(f"✓ Created: {label}")


def append_once(path, marker, content, label):
    text = read(path)
    if marker in text:
        print(f"✓ Already applied: {label}")
        return
    write(path, text.rstrip() + "\n\n" + content.strip() + "\n")
    print(f"✓ Applied: {label}")


replace_once(
    "apps/accounts/models.py",
    '''class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
''',
    '''class User(AbstractUser):
    class NeedType(models.TextChoices):
        LEARN_ORGANISE = (
            "LEARN_ORGANISE",
            "Learn new concepts and organise learning materials",
        )
        PRACTISE_RETAIN = (
            "PRACTISE_RETAIN",
            "Practise and retain knowledge with cards and reviews",
        )
        INTERVIEW_SKILLS = (
            "INTERVIEW_SKILLS",
            "Build interview skills with stories, evidence and mocks",
        )

    username = None
    email = models.EmailField(unique=True)
    primary_need_type = models.CharField(
        max_length=24,
        choices=NeedType.choices,
        blank=True,
        default="",
    )
    secondary_need_type = models.CharField(
        max_length=24,
        choices=NeedType.choices,
        blank=True,
        default="",
    )

    USERNAME_FIELD = "email"
''',
    "user need-type fields",
)

replace_once(
    "apps/accounts/forms.py",
    '''class AccountCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")
''',
    '''class AccountCreationForm(UserCreationForm):
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
''',
    "signup need-type fields",
)

replace_once(
    "apps/accounts/forms.py",
    '''class AccountChangeForm(UserChangeForm):
''',
    '''class NeedTypePreferencesForm(forms.ModelForm):
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
''',
    "need-type preferences form",
)

create_once(
    "apps/accounts/needs.py",
    '''from .models import User


NEED_TYPE_EXPERIENCES = {
    User.NeedType.LEARN_ORGANISE: {
        "title": "Learn and organise",
        "description": (
            "Continue focused roadmaps, import trusted learning material, "
            "and keep your notes and resources together."
        ),
        "action_label": "Open learning roadmaps",
        "route_name": "roadmaps:list",
    },
    User.NeedType.PRACTISE_RETAIN: {
        "title": "Practise and retain",
        "description": (
            "Import or create question cards, strengthen weak areas, "
            "and keep knowledge active through review."
        ),
        "action_label": "Import practice material",
        "route_name": "questions:import_start",
    },
    User.NeedType.INTERVIEW_SKILLS: {
        "title": "Build interview skills",
        "description": (
            "Develop STAR stories, organise evidence, use interview guides, "
            "and practise through mock interviews."
        ),
        "action_label": "Open interview hub",
        "route_name": "interview",
    },
}

NEED_KIND_BONUSES = {
    User.NeedType.LEARN_ORGANISE: {"ROADMAP": 15, "LIBRARY": 10},
    User.NeedType.PRACTISE_RETAIN: {
        "REVIEW": 8,
        "WEAK_AREA": 20,
        "PRACTICE": 25,
        "LIBRARY": 10,
    },
    User.NeedType.INTERVIEW_SKILLS: {
        "REVIEW": 5,
        "WEAK_AREA": 10,
        "PRACTICE": 35,
        "LIBRARY": 8,
    },
}


def need_type_experience(value):
    return NEED_TYPE_EXPERIENCES.get(value)


def need_alignment_for_kind(*, primary, secondary, kind):
    points = 0
    labels = []

    primary_bonus = NEED_KIND_BONUSES.get(primary, {}).get(kind, 0)
    if primary_bonus:
        points += primary_bonus
        labels.append(User.NeedType(primary).label)

    secondary_bonus = NEED_KIND_BONUSES.get(secondary, {}).get(kind, 0)
    if secondary_bonus:
        points += max(1, secondary_bonus // 2)
        labels.append(User.NeedType(secondary).label)

    if not points:
        return 0, ""

    if len(labels) == 1:
        explanation = f"This matches your selected aim: {labels[0]}."
    else:
        explanation = (
            "This supports both of your selected aims: "
            f"{labels[0]} and {labels[1]}."
        )
    return points, explanation
''',
    "need-type experience and planner weights",
)

write(
    "apps/accounts/views.py",
    '''from django.contrib import messages
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
''',
)

replace_once(
    "apps/accounts/urls.py",
    "from .views import SignUpView\n",
    "from .views import SignUpView, need_type_preferences\n",
    "preferences view import",
)
replace_once(
    "apps/accounts/urls.py",
    '    path("signup/", SignUpView.as_view(), name="signup"),\n',
    '''    path("signup/", SignUpView.as_view(), name="signup"),
    path(
        "preferences/",
        need_type_preferences,
        name="need_type_preferences",
    ),
''',
    "preferences route",
)
replace_once(
    "templates/accounts/signup.html",
    '''    <h1>Create your account</h1>
    <form method="post" novalidate>
''',
    '''    <h1>Create your account</h1>
    <p class="lead">
        Tell ViewCoach what you need most. This sets your starting hub and
        helps the daily planner prioritise useful work.
    </p>
    <form method="post" novalidate>
''',
    "signup aim explanation",
)

create_once(
    "templates/accounts/need_type_preferences.html",
    '''{% extends "base.html" %}

{% block title %}Preparation aims | ViewCoach{% endblock %}

{% block content %}
<section class="form-card need-preferences-card">
    <p class="eyebrow">Personalisation</p>
    <h1>What should ViewCoach prioritise?</h1>
    <p class="lead">
        Your aims influence dashboard prompts and planner scoring. They do
        not hide any part of ViewCoach.
    </p>
    <form method="post" novalidate>
        {% csrf_token %}
        {{ form.non_field_errors }}
        {% for field in form %}
            <div class="form-field">
                {{ field.label_tag }}
                {{ field }}
                {{ field.errors }}
            </div>
        {% endfor %}
        <div class="need-preferences-actions">
            <button class="button" type="submit">Save aims</button>
            <a class="button button-secondary" href="{% url 'dashboard' %}">
                Cancel
            </a>
        </div>
    </form>
</section>
{% endblock %}
''',
    "need-type preferences template",
)

replace_once(
    "templates/includes/app_account_menu.html",
    '        <span class="app-account-disabled">Settings <small>Coming soon</small></span>\n',
    '        <a href="{% url \'need_type_preferences\' %}">Preparation aims</a>\n',
    "account-menu preferences link",
)

replace_once(
    "apps/core/views.py",
    "from apps.evidence.services import evidence_dashboard_summary\n",
    "from apps.accounts.needs import need_type_experience\nfrom apps.evidence.services import evidence_dashboard_summary\n",
    "dashboard need-type import",
)
replace_once(
    "apps/core/views.py",
    '''    evidence_summary = evidence_dashboard_summary(user=request.user)
    viewcoach_groups = grouped_viewcoach_roadmap_cards(user=request.user)
''',
    '''    evidence_summary = evidence_dashboard_summary(user=request.user)
    need_focus = need_type_experience(request.user.primary_need_type)
    viewcoach_groups = grouped_viewcoach_roadmap_cards(user=request.user)
''',
    "dashboard need-focus preparation",
)
replace_once(
    "apps/core/views.py",
    '''            "evidence_summary": evidence_summary,
            "viewcoach_learning_cards": _prioritised_learning_cards(viewcoach_groups),
''',
    '''            "evidence_summary": evidence_summary,
            "need_focus": need_focus,
            "viewcoach_learning_cards": _prioritised_learning_cards(viewcoach_groups),
''',
    "dashboard need-focus context",
)

replace_once(
    "templates/core/dashboard.html",
    '    <section class="dashboard-v2-stats" aria-label="Preparation summary">\n',
    '''    <section class="dashboard-v2-card dashboard-need-focus"
             aria-labelledby="dashboard-need-focus-heading">
        {% if need_focus %}
            <div>
                <p class="dashboard-v2-kicker">Your primary aim</p>
                <h2 id="dashboard-need-focus-heading">{{ need_focus.title }}</h2>
                <p>{{ need_focus.description }}</p>
            </div>
            <div class="dashboard-need-focus-actions">
                <a class="button" href="{% url need_focus.route_name %}">
                    {{ need_focus.action_label }}
                </a>
                <a href="{% url 'need_type_preferences' %}">Change aims</a>
            </div>
        {% else %}
            <div>
                <p class="dashboard-v2-kicker">Personalise ViewCoach</p>
                <h2 id="dashboard-need-focus-heading">Choose what you need most</h2>
                <p>
                    Set a primary aim so the dashboard and daily planner can
                    prioritise the right kind of preparation.
                </p>
            </div>
            <div class="dashboard-need-focus-actions">
                <a class="button" href="{% url 'need_type_preferences' %}">
                    Choose my aim
                </a>
            </div>
        {% endif %}
    </section>

    <section class="dashboard-v2-stats" aria-label="Preparation summary">
''',
    "dashboard primary-aim panel",
)

replace_once(
    "apps/planner/candidates.py",
    '''    deadline_days: int | None = None

    description: str = ""
''',
    '''    deadline_days: int | None = None
    aim_alignment_bonus: int = 0
    aim_alignment_explanation: str = ""

    description: str = ""
''',
    "planner candidate aim fields",
)
replace_once(
    "apps/planner/scoring.py",
    '''    deadline_component = _deadline_component(candidate.deadline_days)
''',
    '''    if candidate.aim_alignment_bonus:
        components.append(
            ScoreComponent(
                key="selected_aim",
                points=candidate.aim_alignment_bonus,
                explanation=candidate.aim_alignment_explanation,
            )
        )

    deadline_component = _deadline_component(candidate.deadline_days)
''',
    "planner aim score component",
)
replace_once(
    "apps/planner/candidate_builders.py",
    "from dataclasses import dataclass\n",
    "from dataclasses import dataclass, replace\n",
    "candidate replace import",
)
replace_once(
    "apps/planner/candidate_builders.py",
    "from apps.goals.models import InterviewGoal\n",
    "from apps.accounts.needs import need_alignment_for_kind\nfrom apps.goals.models import InterviewGoal\n",
    "need alignment import",
)
replace_once(
    "apps/planner/candidate_builders.py",
    "def build_plan_candidates(\n",
    '''def _apply_need_alignment(*, user, candidates):
    aligned = []
    for candidate in candidates:
        bonus, explanation = need_alignment_for_kind(
            primary=user.primary_need_type,
            secondary=user.secondary_need_type,
            kind=candidate.kind.value,
        )
        aligned.append(
            replace(
                candidate,
                aim_alignment_bonus=bonus,
                aim_alignment_explanation=explanation,
            )
        )
    return aligned


def build_plan_candidates(
''',
    "need alignment helper",
)
replace_once(
    "apps/planner/candidate_builders.py",
    '''    return CandidateBuildResult(
        candidates=tuple(candidates),
''',
    '''    aligned_candidates = _apply_need_alignment(
        user=user,
        candidates=candidates,
    )

    return CandidateBuildResult(
        candidates=tuple(aligned_candidates),
''',
    "apply aim alignment",
)

create_once(
    "apps/accounts/migrations/0002_user_need_types.py",
    '''from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="primary_need_type",
            field=models.CharField(
                blank=True,
                choices=[
                    (
                        "LEARN_ORGANISE",
                        "Learn new concepts and organise learning materials",
                    ),
                    (
                        "PRACTISE_RETAIN",
                        "Practise and retain knowledge with cards and reviews",
                    ),
                    (
                        "INTERVIEW_SKILLS",
                        "Build interview skills with stories, evidence and mocks",
                    ),
                ],
                default="",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="secondary_need_type",
            field=models.CharField(
                blank=True,
                choices=[
                    (
                        "LEARN_ORGANISE",
                        "Learn new concepts and organise learning materials",
                    ),
                    (
                        "PRACTISE_RETAIN",
                        "Practise and retain knowledge with cards and reviews",
                    ),
                    (
                        "INTERVIEW_SKILLS",
                        "Build interview skills with stories, evidence and mocks",
                    ),
                ],
                default="",
                max_length=24,
            ),
        ),
    ]
''',
    "accounts migration",
)

replace_once(
    "apps/accounts/tests/test_authentication.py",
    '''            "last_name": "",
            "password1": "A-safe-test-password-123",
''',
    '''            "last_name": "",
            "primary_need_type": User.NeedType.LEARN_ORGANISE,
            "secondary_need_type": "",
            "password1": "A-safe-test-password-123",
''',
    "registration test aim",
)
replace_once(
    "apps/accounts/tests/test_authentication.py",
    '    assert response.url == reverse("dashboard")\n',
    '    assert response.url == reverse("roadmaps:list")\n',
    "registration test destination",
)
replace_once(
    "apps/accounts/tests/test_authentication.py",
    '''            "last_name": "User",
            "password1": "A-safe-test-password-123",
''',
    '''            "last_name": "User",
            "primary_need_type": User.NeedType.PRACTISE_RETAIN,
            "secondary_need_type": "",
            "password1": "A-safe-test-password-123",
''',
    "duplicate email test aim",
)

create_once(
    "apps/accounts/tests/test_need_types.py",
    '''import pytest
from django.urls import reverse

from apps.accounts.forms import NeedTypePreferencesForm
from apps.accounts.models import User
from apps.accounts.needs import need_alignment_for_kind

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("need_type", "destination"),
    [
        (User.NeedType.LEARN_ORGANISE, "roadmaps:list"),
        (User.NeedType.PRACTISE_RETAIN, "questions:import_start"),
        (User.NeedType.INTERVIEW_SKILLS, "interview"),
    ],
)
def test_signup_routes_user_to_primary_need_hub(client, need_type, destination):
    response = client.post(
        reverse("signup"),
        {
            "email": f"{need_type.lower()}@example.com",
            "first_name": "Tee",
            "last_name": "",
            "primary_need_type": need_type,
            "secondary_need_type": "",
            "password1": "A-safe-test-password-123",
            "password2": "A-safe-test-password-123",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse(destination)


def test_user_can_update_aims(client, user):
    client.force_login(user)
    response = client.post(
        reverse("need_type_preferences"),
        {
            "primary_need_type": User.NeedType.INTERVIEW_SKILLS,
            "secondary_need_type": User.NeedType.PRACTISE_RETAIN,
        },
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.primary_need_type == User.NeedType.INTERVIEW_SKILLS
    assert user.secondary_need_type == User.NeedType.PRACTISE_RETAIN


def test_secondary_aim_must_differ_from_primary(user):
    form = NeedTypePreferencesForm(
        data={
            "primary_need_type": User.NeedType.LEARN_ORGANISE,
            "secondary_need_type": User.NeedType.LEARN_ORGANISE,
        },
        instance=user,
    )

    assert form.is_valid() is False
    assert "secondary_need_type" in form.errors


def test_interview_aim_boosts_practice():
    points, explanation = need_alignment_for_kind(
        primary=User.NeedType.INTERVIEW_SKILLS,
        secondary="",
        kind="PRACTICE",
    )

    assert points == 35
    assert "Build interview skills" in explanation
''',
    "need type tests",
)

append_once(
    "static/css/visual-identity-v1.css",
    ".dashboard-need-focus",
    '''.dashboard-need-focus {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
    margin-bottom: 1.25rem;
}

.dashboard-need-focus p {
    max-width: 48rem;
    margin-bottom: 0;
}

.dashboard-need-focus-actions {
    display: grid;
    gap: 0.7rem;
    justify-items: start;
}

.need-preferences-card {
    max-width: 48rem;
}

.need-preferences-card ul {
    display: grid;
    gap: 0.7rem;
    padding: 0;
    list-style: none;
}

.need-preferences-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-top: 1.25rem;
}

@media (max-width: 42rem) {
    .dashboard-need-focus {
        align-items: flex-start;
        flex-direction: column;
    }
}
''',
    "need type styles",
)

print("\nPatch 3B applied.")
print("Run: python manage.py migrate")
print("Then run the checks in the patch notes.")
