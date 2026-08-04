from pathlib import Path

from django.conf import settings


def _read(relative_path: str) -> str:
    return (Path(settings.BASE_DIR) / relative_path).read_text()


def test_shell_uses_grouped_navigation_and_preparation_stages():
    base = _read("templates/base.html")
    navigation = _read("templates/includes/app_primary_navigation_v3.html")

    assert "proofloop-workspace.css" in base
    assert "proofloop-shell-stages" in base
    assert "Build a preparation loop you can measure and explain." in base
    assert "proofloop-sidebar-loop" in base

    for label in ("Command", "Build", "Prove", "Library"):
        assert f">{label}<" in navigation


def test_dashboard_is_a_structural_readiness_command_centre():
    dashboard = _read("templates/core/proofloop_dashboard.html")
    views = _read("apps/core/views.py")

    assert 'core/proofloop_dashboard.html' in views

    for marker in (
        "proofloop-command-hero",
        "proofloop-loop-map",
        "proofloop-signal-strip",
        "proofloop-dashboard-grid",
        "proofloop-readiness-panel",
        "proofloop-evidence-layers",
        "proofloop-deadline-callout",
    ):
        assert marker in dashboard

    assert "Plan → Learn → Retain → Prove → Rehearse" in dashboard
    assert "Preparation command centre" in dashboard
    assert "ProofLoop selected this" in dashboard


def test_dashboard_preserves_existing_product_contract_labels():
    dashboard = _read("templates/core/proofloop_dashboard.html")

    for label in (
        "Continue preparing",
        "Your focused roadmaps",
        "Your learning journey",
        "Today’s plan",
        "Evidence Bag",
        "Interview readiness",
        "Recently updated questions",
    ):
        assert label in dashboard


def test_workspace_styles_define_desktop_and_mobile_composition():
    stylesheet = _read("static/css/proofloop-workspace.css")

    assert "grid-template-areas" in stylesheet
    assert ".proofloop-plan-panel { order: 1; }" in stylesheet
    assert ".proofloop-journey-panel { order: 2; }" in stylesheet
    assert ".proofloop-roadmaps-panel { order: 3; }" in stylesheet
    assert ".proofloop-readiness-panel { order: 4; }" in stylesheet
    assert ".proofloop-calendar-panel { order: 8; }" in stylesheet
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet
