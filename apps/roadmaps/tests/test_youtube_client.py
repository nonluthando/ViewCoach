import pytest

from apps.roadmaps.youtube_client import (
    extract_playlist_id,
    format_duration,
    parse_iso8601_duration,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "https://www.youtube.com/playlist?list=PL1234567890ABC",
            "PL1234567890ABC",
        ),
        (
            "https://www.youtube.com/watch?v=abc&list=PL1234567890ABC",
            "PL1234567890ABC",
        ),
        ("PL1234567890ABC", "PL1234567890ABC"),
    ],
)
def test_extract_playlist_id(value, expected):
    assert extract_playlist_id(value) == expected


def test_extract_playlist_id_rejects_non_youtube_host():
    with pytest.raises(ValueError, match="YouTube"):
        extract_playlist_id("https://example.com/playlist?list=PL1234567890ABC")


@pytest.mark.parametrize(
    ("value", "seconds"),
    [
        ("PT12M5S", 725),
        ("PT1H2M3S", 3723),
        ("P1DT2H", 93600),
        ("PT45S", 45),
    ],
)
def test_parse_iso8601_duration(value, seconds):
    assert parse_iso8601_duration(value) == seconds


def test_format_duration():
    assert format_duration(65) == "1:05"
    assert format_duration(3723) == "1:02:03"
