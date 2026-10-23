"""Explainable rules producing exact, checkable evidence (D-017).

R1 — parameter mismatch: the docstring documents a parameter the current signature lacks.
     Train-split rates: 15.3% of stale vs 7.4% of updated docstrings (docs/FEASIBILITY.md F5).
R2 — deleted-identifier mention: the docstring mentions an identifier token that appears
     only in removed code lines. Adapted from OVERLAP(C, deleted) (Panthaplackel et al.,
     AAAI 2021; docs/REFERENCES.md R4). Train-split rates: 27.8% vs 17.7% (F6).
"""

from __future__ import annotations

import ast
import warnings
from dataclasses import dataclass, field

import docstring_parser

from spequlator.nlp.preprocessing import code_diff, content_tokens, dedent_code

_IMPLICIT = frozenset({"self", "cls"})


def _first_function(code: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)  # invalid escapes in old code
            tree = ast.parse(dedent_code(code))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    return None


@dataclass(frozen=True)
class Signature:
    params: frozenset[str]
    has_var_keyword: bool  # **kwargs present
    def_line: str


def parse_signature(code: str) -> Signature | None:
    """Parameter names of the first function in ``code`` (``self``/``cls`` dropped)."""
    fn = _first_function(code)
    if fn is None:
        return None
    a = fn.args
    names = {x.arg for x in (*a.posonlyargs, *a.args, *a.kwonlyargs)}
    if a.vararg:
        names.add(a.vararg.arg)
    if a.kwarg:
        names.add(a.kwarg.arg)
    def_line = next(
        (ln.strip() for ln in code.splitlines() if ln.strip().startswith(("def ", "async def "))),
        "",
    )
    return Signature(frozenset(names - _IMPLICIT), a.kwarg is not None, def_line)


def documented_params(doc: str) -> frozenset[str]:
    """Parameter names documented in reST, Google or NumPy style (docstring_parser, R14)."""
    try:
        parsed = docstring_parser.parse(doc)
    except Exception:  # noqa: BLE001 - third-party parser on arbitrary text must never crash analysis
        return frozenset()
    names = set()
    for p in parsed.params:
        if p.arg_name:
            name = p.arg_name.split()[0].lstrip("*").strip(":,")
            if name.isidentifier():
                names.add(name)
    return frozenset(names - _IMPLICIT)


@dataclass(frozen=True)
class R1Result:
    applicable: bool  # signature parsed and the docstring documents parameters
    fired: bool
    stale_params: list[str] = field(default_factory=list)  # documented, not in signature
    undocumented_params: list[str] = field(default_factory=list)  # in signature, not documented
    def_line: str = ""


def param_mismatch(doc: str, code: str) -> R1Result:
    """R1. Suppressed when the function takes ``**kwargs`` (documented keys may flow through it)."""
    sig = parse_signature(code)
    documented = documented_params(doc)
    if sig is None or not documented:
        return R1Result(applicable=False, fired=False, def_line=sig.def_line if sig else "")
    stale = sorted(documented - sig.params)
    undocumented = sorted(sig.params - documented)
    fired = bool(stale) and not sig.has_var_keyword
    return R1Result(True, fired, stale, undocumented, sig.def_line)


@dataclass(frozen=True)
class R2Result:
    applicable: bool  # change mode with at least one removed line
    fired: bool
    tokens: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)  # removed lines containing the tokens (max 3)


def deleted_identifier_mentions(doc: str, old_code: str, new_code: str) -> R2Result:
    """R2. Docstring tokens that occur in removed lines and nowhere in the new code."""
    diff = code_diff(old_code, new_code)
    if not diff.removed:
        return R2Result(applicable=False, fired=False)
    gone = content_tokens("\n".join(diff.removed)) - content_tokens(new_code)
    hits = sorted(content_tokens(doc) & gone)
    lines = [ln.strip() for ln in diff.removed if content_tokens(ln) & set(hits)][:3]
    return R2Result(applicable=True, fired=bool(hits), tokens=hits, lines=lines)
