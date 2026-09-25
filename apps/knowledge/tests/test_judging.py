import pytest

from apps.knowledge.judging import FaithfulnessJudgeError, _parse_verdict


def test_parse_verdict_reads_faithful_true():
    verdict = _parse_verdict('{"faithful": true, "reasoning": "Matches source."}')

    assert verdict.faithful is True
    assert verdict.reasoning == "Matches source."


def test_parse_verdict_reads_faithful_false():
    verdict = _parse_verdict('{"faithful": false, "reasoning": "Adds an unsupported claim."}')

    assert verdict.faithful is False
    assert verdict.reasoning == "Adds an unsupported claim."


def test_parse_verdict_defaults_missing_reasoning_to_empty_string():
    verdict = _parse_verdict('{"faithful": true}')

    assert verdict.reasoning == ""


@pytest.mark.parametrize(
    "raw_output",
    [
        "",
        "   ",
        "not json at all",
        '{"reasoning": "missing the faithful key"}',
        "[]",
    ],
)
def test_parse_verdict_raises_on_unparseable_output(raw_output):
    with pytest.raises(FaithfulnessJudgeError):
        _parse_verdict(raw_output)
