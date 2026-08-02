import pytest

from apps.roadmaps.ibm_client import (
    normalize_ibm_course_url,
    parse_ibm_course_html,
)

PUBLIC_COURSE_HTML = """
<html lang="en">
<head>
  <meta property="og:title" content="AI Foundations">
  <meta property="og:description" content="An introduction to AI.">
</head>
<body>
  <h1>AI Foundations</h1>
  <p>Duration</p><p>14 hours</p>
  <h2>Course content</h2>
  <h3>Module 1</h3><p>What is AI?</p><p>2h 15min</p>
  <h3>Module 2</h3><p>AI and you</p><p>3 hours</p>
  <h3>Assessment</h3><p>Final assessment</p><p>30min</p>
</body>
</html>
"""


def test_public_ibm_course_metadata_and_outline_are_extracted():
    preview = parse_ibm_course_html(
        source_url="https://skillsbuild.org/students/course-catalog/ai",
        html=PUBLIC_COURSE_HTML,
    )
    assert preview.title == "AI Foundations"
    assert preview.duration_minutes == 840
    assert [item.module_title for item in preview.outline] == [
        "Module 1",
        "Module 2",
        "Assessment",
    ]
    assert preview.outline[0].lesson_title == "What is AI?"
    assert preview.outline[0].duration_minutes == 135


@pytest.mark.parametrize(
    "value",
    [
        "http://skillsbuild.org/course",
        "https://example.com/course",
        "https://skillsbuild.org:8443/course",
    ],
)
def test_ibm_course_url_rejects_untrusted_locations(value):
    with pytest.raises(ValueError):
        normalize_ibm_course_url(value)
