"""Text preprocessing utilities for Spequlator.

Identifier splitting follows the standard CamelCase/underscore approach shown to be
competitive for IR on code (Dit et al., ICPC 2011; docs/REFERENCES.md R13).
"""

from __future__ import annotations

import difflib
import keyword
import re
import textwrap
from dataclasses import dataclass, field

_ACRONYM = re.compile(r"([A-Z]+)([A-Z][a-z])")  # HTTPResponse -> HTTP Response
_CAMEL = re.compile(r"([a-z0-9])([A-Z])")  # getUser -> get User
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]+")  # letters/digits, length >= 2

# Words too generic to count as evidence for rule R2 (deleted-identifier mention).
STOPWORDS: frozenset[str] = frozenset(
    {k.lower() for k in keyword.kwlist}
    | {
        "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "by", "at",
        "from", "as", "is", "are", "be", "been", "was", "were", "it", "its", "this", "that",
        "these", "those", "if", "else", "then", "than", "not", "no", "can", "will", "should",
        "may", "must", "into", "when", "which", "who", "what", "how", "all", "any", "each",
        "other", "some", "such", "only", "also", "use", "used", "using", "new", "old", "get",
        "set", "self", "cls", "none", "true", "false", "args", "kwargs", "arg", "param",
        "params", "return", "returns", "type", "str", "int", "float", "bool", "list", "dict",
        "tuple", "object", "optional", "default", "value", "values", "data", "name", "see",
    }
)  # fmt: skip


def normalize_text(text: str) -> str:
    """Normalize whitespace without removing meaningful code syntax."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    return re.sub(r"\s+", " ", text).strip()


def split_identifiers(text: str) -> list[str]:
    """Split code/prose into lowercase word tokens, breaking CamelCase and snake_case.

    >>> split_identifiers("getHTTPResponse_code(x)")
    ['get', 'http', 'response', 'code']
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    text = _ACRONYM.sub(r"\1 \2", text)
    text = _CAMEL.sub(r"\1 \2", text).replace("_", " ")
    return [w.lower() for w in _WORD.findall(text)]


def content_tokens(text: str, min_len: int = 3) -> set[str]:
    """Distinct identifier tokens worth citing as evidence (no stopwords, len >= min_len)."""
    return {t for t in split_identifiers(text) if len(t) >= min_len and t not in STOPWORDS}


def dedent_code(code: str) -> str:
    """Remove common leading indentation so ``ast`` can parse methods extracted from classes."""
    return textwrap.dedent(code).strip("\n")


@dataclass(frozen=True)
class DiffParts:
    """Line-level code change. ``removed``/``added`` exclude unchanged lines."""

    removed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.removed or self.added)


def parse_ndiff(diff: str) -> DiffParts:
    """Parse ``difflib.ndiff`` text (CoDocBench's diff format). ``? `` hint lines are ignored."""
    removed, added = [], []
    for line in diff.splitlines():
        if line.startswith("- "):
            if line[2:].strip():
                removed.append(line[2:])
        elif line.startswith("+ ") and line[2:].strip():
            added.append(line[2:])
    return DiffParts(removed=removed, added=added)


def code_diff(old_code: str, new_code: str) -> DiffParts:
    """Diff two code versions with ``difflib.ndiff`` (same format as CoDocBench's ``diff_code``)."""
    lines = difflib.ndiff(old_code.splitlines(), new_code.splitlines())
    return parse_ndiff("\n".join(lines))
