from pathlib import Path

from django.conf import settings


def _read(relative_path: str) -> str:
    return (Path(settings.BASE_DIR) / relative_path).read_text()


def test_customer_facing_shell_uses_proofloop_brand():
    base = _read("templates/base.html")

    assert "{% block title %}ProofLoop{% endblock %}" in base
    assert "proofloop.css" in base
    assert base.count("proofloop-mark") >= 3
    assert "Adaptive interview-readiness workspace" in base


def test_landing_page_uses_readiness_positioning():
    landing = _read("templates/core/landing_page.html")

    assert "ProofLoop | Adaptive interview-readiness workspace" in landing
    assert "Turn preparation into a loop you can trust." in landing
    assert "formerly ViewCoach" in landing
    assert "Readiness overview" in landing
    assert "Four preparation layers" in landing
    assert "Try the recruiter demo" not in landing


def test_demo_and_case_study_use_public_brand_language():
    demo = _read("templates/core/portfolio_demo_guide.html")
    banner = _read("templates/includes/portfolio_demo_banner.html")
    showcase = _read("templates/core/project_showcase.html")

    assert "Demo | ProofLoop" in demo
    assert "ProofLoop workflows" in demo
    assert "ProofLoop demo" in banner
    assert "Recruiter demo" not in banner
    assert "ProofLoop turns scattered interview preparation" in showcase
    assert "Start recruiter demo" not in showcase


def test_proofloop_theme_exposes_locked_visual_tokens():
    stylesheet = _read("static/css/proofloop.css")

    for token in (
        "--proofloop-ink",
        "--proofloop-cream",
        "--proofloop-emerald",
        "--proofloop-amber",
    ):
        assert token in stylesheet

    assert ".proofloop-path" in stylesheet
    assert ".proofloop-evidence-stack" in stylesheet
    assert ".dashboard-v3-readiness" in stylesheet
