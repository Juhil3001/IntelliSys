import json

import pytest

from app.modules.ai_insights.scan_analyzer import _parse_json_response


def test_parse_json_response_plain() -> None:
    d = _parse_json_response('{"issues":[]}')
    assert d == {"issues": []}


def test_parse_json_response_fenced() -> None:
    text = '```json\n{"issues": [{"type": "ai_x", "description": "d", "severity": "low"}]}\n```'
    d = _parse_json_response(text)
    assert "issues" in d


def test_parse_json_response_invalid() -> None:
    with pytest.raises((json.JSONDecodeError, ValueError)):
        _parse_json_response("not json")
