from apps.planner.forms import StudyPlanPreferencesForm


def test_study_time_accepts_twelve_hours():
    form = StudyPlanPreferencesForm({"time_budget_hours": "12"})

    assert form.is_valid()
    assert form.cleaned_data["time_budget_minutes"] == 720


def test_study_time_rejects_more_than_sixteen_hours():
    form = StudyPlanPreferencesForm({"time_budget_hours": "16.25"})

    assert not form.is_valid()
    assert "time_budget_hours" in form.errors


def test_study_time_rejects_non_quarter_hour_increment():
    form = StudyPlanPreferencesForm({"time_budget_hours": "1.1"})

    assert not form.is_valid()
    assert "Use 15-minute increments." in form.errors["time_budget_hours"]
