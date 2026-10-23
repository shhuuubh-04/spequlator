import pytest

from spequlator.nlp.preprocessing import normalize_text


def test_normalize_whitespace():
    assert normalize_text("  hello \n world  ") == "hello world"


def test_preserves_code_syntax():
    code = "if (user_id != None):"
    assert normalize_text(code) == code


def test_rejects_non_string_input():
    with pytest.raises(TypeError):
        normalize_text(None)
