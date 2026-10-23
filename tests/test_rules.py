import pytest

from spequlator.nlp.rules import (
    deleted_identifier_mentions,
    documented_params,
    param_mismatch,
    parse_signature,
)

REST = "Do it.\n\n:param path: where.\n:param mode: how.\n"
GOOGLE = "Do it.\n\nArgs:\n    path (str): where.\n    mode: how.\n"
NUMPY = "Do it.\n\nParameters\n----------\npath : str\n    where.\nmode : str\n    how.\n"


@pytest.mark.parametrize("doc", [REST, GOOGLE, NUMPY])
def test_documented_params_styles(doc):
    assert documented_params(doc) == {"path", "mode"}


def test_documented_params_none_and_garbage():
    assert documented_params("Just a sentence.") == frozenset()
    assert documented_params(":param:::\n Args:\n  ???") == frozenset()


def test_parse_signature_method_async_and_varargs():
    code = "    async def run(self, job, *items, retries=3, **opts):\n        pass\n"
    sig = parse_signature(code)
    assert sig is not None
    assert sig.params == {"job", "items", "retries", "opts"}
    assert sig.has_var_keyword
    assert sig.def_line.startswith("async def run(")


def test_parse_signature_unparseable():
    assert parse_signature("def broken(:\n") is None


def test_r1_fires_on_removed_param():
    r = param_mismatch(REST, "def save(path):\n    pass\n")
    assert r.applicable and r.fired
    assert r.stale_params == ["mode"]


def test_r1_quiet_when_params_match():
    r = param_mismatch(GOOGLE, "def save(path, mode='w'):\n    pass\n")
    assert r.applicable and not r.fired


def test_r1_suppressed_with_kwargs():
    r = param_mismatch(REST, "def save(path, **kwargs):\n    pass\n")
    assert r.applicable and not r.fired
    assert r.stale_params == ["mode"]  # still reported, just not decisive


def test_r1_not_applicable_without_documented_params():
    assert not param_mismatch("Save the file.", "def save(path):\n    pass\n").applicable


OLD = "def load(path, use_cache=True):\n    if use_cache:\n        return cache_lookup(path)\n    return read(path)\n"
NEW = "def load(path):\n    return read(path)\n"


def test_r2_fires_on_removed_identifier():
    r = deleted_identifier_mentions("Load a file, using the lookup cache when enabled.", OLD, NEW)
    assert r.applicable and r.fired
    assert {"cache", "lookup"} <= set(r.tokens)
    assert r.lines and all("cache" in ln for ln in r.lines)


def test_r2_quiet_when_token_survives():
    r = deleted_identifier_mentions("Read the file at path.", OLD, NEW)
    assert r.applicable and not r.fired  # 'read' and 'path' remain in the new code


def test_r2_not_applicable_without_removed_lines():
    assert not deleted_identifier_mentions("Doc.", NEW, NEW + "\n# extra\n").applicable
