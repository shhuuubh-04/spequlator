import pytest

from spequlator.nlp.preprocessing import (
    code_diff,
    content_tokens,
    normalize_text,
    parse_ndiff,
    split_identifiers,
)


def test_normalize_whitespace():
    assert normalize_text("  hello \n world  ") == "hello world"


def test_preserves_code_syntax():
    code = "if (user_id != None):"
    assert normalize_text(code) == code


def test_rejects_non_string_input():
    with pytest.raises(TypeError):
        normalize_text(None)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("getHTTPResponse_code", ["get", "http", "response", "code"]),
        ("observe_lr(optimizer_name='main')", ["observe", "lr", "optimizer", "name", "main"]),
        ("XMLParser.parseString", ["xml", "parser", "parse", "string"]),
        ("x = 1", []),  # single letters and numbers dropped
        ("", []),
    ],
)
def test_split_identifiers(text, expected):
    assert split_identifiers(text) == expected


def test_split_identifiers_rejects_non_string():
    with pytest.raises(TypeError):
        split_identifiers(None)


def test_content_tokens_drop_stopwords_and_short_tokens():
    assert content_tokens("Return the retry_count for self.db") == {"retry", "count"}


def test_parse_ndiff_ignores_hint_and_blank_lines():
    diff = "  def f(a):\n-     return a\n?            ^\n+     return a + 1\n-    \n"
    parts = parse_ndiff(diff)
    assert parts.removed == ["    return a"]
    assert parts.added == ["    return a + 1"]
    assert parts.changed


def test_code_diff_unchanged():
    assert not code_diff("def f(): pass", "def f(): pass").changed
