"""Top-level declaration parsing for Lean source text.

This module is a toolkit-owned lightweight parser. It was designed with similar
goals to the source-oriented analysis utilities in LongCat-Flash-Prover:
https://github.com/zhangjf-nlp/LongCat-Flash-Prover

It does not reuse upstream code verbatim; it implements a smaller parser
specialized for toolkit declaration/no_sorry/direct-axiom workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from .comments import mask_comments_and_strings
from .models import ParsedLeanModule, TextAstDeclaration, TextAstPosition
from .namespace import qualify_name

_DECL_RE = re.compile(
    r"^(?P<kw>theorem|lemma|def|abbrev|instance|axiom|constant|opaque|structure|class|inductive)\b(?P<rest>.*)$"
)
_NAMESPACE_RE = re.compile(r"^namespace\s+(?P<name>[A-Za-z0-9_'.]+)\b")
_SECTION_RE = re.compile(r"^section(?:\s+(?P<name>[A-Za-z0-9_'.]+))?\b")
_END_RE = re.compile(r"^end(?:\s+(?P<name>[A-Za-z0-9_'.]+))?\b")
_ALIAS_RE = re.compile(r"^alias\s+.+?:=\s+(?P<export>[A-Za-z0-9_'.]+)\s*$")
_SIMPLE_NAME_RE = re.compile(r"^(?P<name>[A-Za-z0-9_'.]+)")


@dataclass(slots=True, frozen=True)
class _PendingDoc:
    text: str
    start_line: int
    end_line: int


def parse_declarations(*, text: str, module_dot: str) -> ParsedLeanModule:
    masked = mask_comments_and_strings(text)
    lines = text.splitlines()
    masked_lines = masked.splitlines()
    namespace_stack: list[str] = []
    section_stack: list[str | None] = []
    alias_exports: list[str] = []
    pending_doc: _PendingDoc | None = None
    decl_starts: list[tuple[int, int, int, str, str, str, _PendingDoc | None]] = []
    top_level_boundaries: list[int] = []

    line_idx = 0
    while line_idx < len(lines):
        original = lines[line_idx]
        masked_line = masked_lines[line_idx] if line_idx < len(masked_lines) else original
        stripped = original.strip()
        masked_stripped = masked_line.strip()

        if not stripped:
            pending_doc = None if pending_doc is not None else None
            line_idx += 1
            continue

        if not original[:1].isspace():
            if stripped.startswith("/--"):
                doc_lines = [original]
                start_line = line_idx + 1
                while "-/" not in doc_lines[-1] and line_idx + 1 < len(lines):
                    line_idx += 1
                    doc_lines.append(lines[line_idx])
                pending_doc = _PendingDoc(
                    text="\n".join(doc_lines),
                    start_line=start_line,
                    end_line=line_idx + 1,
                )
                line_idx += 1
                continue

            match = _NAMESPACE_RE.match(masked_stripped)
            if match is not None:
                top_level_boundaries.append(line_idx)
                namespace_stack.append(match.group("name"))
                pending_doc = None
                line_idx += 1
                continue

            match = _SECTION_RE.match(masked_stripped)
            if match is not None:
                top_level_boundaries.append(line_idx)
                section_stack.append(match.group("name"))
                pending_doc = None
                line_idx += 1
                continue

            match = _END_RE.match(masked_stripped)
            if match is not None:
                top_level_boundaries.append(line_idx)
                end_name = (match.group("name") or "").strip()
                if section_stack:
                    if section_stack[-1] is None or section_stack[-1] == end_name:
                        section_stack.pop()
                    elif namespace_stack and namespace_stack[-1] == end_name:
                        namespace_stack.pop()
                elif namespace_stack:
                    if not end_name or namespace_stack[-1] == end_name:
                        namespace_stack.pop()
                pending_doc = None
                line_idx += 1
                continue

            match = _ALIAS_RE.match(masked_stripped)
            if match is not None:
                top_level_boundaries.append(line_idx)
                export = match.group("export").strip()
                if export:
                    if export not in alias_exports:
                        alias_exports.append(export)
                pending_doc = None
                line_idx += 1
                continue

            match = _DECL_RE.match(masked_stripped)
            if match is not None:
                kind = match.group("kw").strip().lower()
                short_name = _extract_decl_name(kind=kind, rest=match.group("rest").strip(), line_no=line_idx + 1)
                if short_name is not None:
                    full_name = qualify_name(
                        namespace_stack=tuple(namespace_stack),
                        raw_name=short_name,
                    )
                    decl_starts.append(
                        (
                            (pending_doc.start_line - 1) if pending_doc is not None else line_idx,
                            line_idx,
                            line_idx + 1,
                            kind,
                            short_name,
                            full_name,
                            pending_doc,
                        )
                    )
                    pending_doc = None
                    line_idx += 1
                    continue

        pending_doc = None
        if not original[:1].isspace():
            top_level_boundaries.append(line_idx)
        line_idx += 1

    declarations: list[TextAstDeclaration] = []
    for idx, (full_start_idx, body_start_idx, start_line, kind, short_name, full_name, doc) in enumerate(
        decl_starts
    ):
        next_start = decl_starts[idx + 1][0] if idx + 1 < len(decl_starts) else len(lines)
        for boundary_idx in top_level_boundaries:
            if boundary_idx > body_start_idx:
                next_start = min(next_start, boundary_idx)
                break
        end_exclusive = next_start
        while end_exclusive > body_start_idx and not lines[end_exclusive - 1].strip():
            end_exclusive -= 1
        body_lines = lines[body_start_idx:end_exclusive]
        block_lines = lines[full_start_idx:end_exclusive]
        body_text = "\n".join(body_lines).rstrip()
        block_text = "\n".join(block_lines).rstrip()
        header = body_lines[0].strip() if body_lines else ""
        signature, value = _split_signature_and_value(
            kind=kind,
            short_name=short_name,
            header=header,
            body=body_text,
        )
        end_line_idx = max(body_start_idx, end_exclusive - 1)
        end_col = len(lines[end_line_idx]) if end_line_idx < len(lines) else 0
        declarations.append(
            TextAstDeclaration(
                name=full_name,
                short_name=short_name,
                kind=_normalize_kind(kind),
                signature=signature,
                value=value,
                full_declaration=block_text or None,
                docstring=(doc.text if doc is not None else None),
                decl_start_pos=TextAstPosition(line=full_start_idx + 1, column=0),
                decl_end_pos=TextAstPosition(line=end_line_idx + 1, column=end_col),
                doc_start_pos=(
                    TextAstPosition(line=doc.start_line, column=0) if doc is not None else None
                ),
                doc_end_pos=(
                    TextAstPosition(
                        line=doc.end_line,
                        column=len(lines[doc.end_line - 1]) if 0 <= doc.end_line - 1 < len(lines) else 0,
                    )
                    if doc is not None
                    else None
                ),
            )
        )

    return ParsedLeanModule(
        declarations=tuple(declarations),
        alias_exports=tuple(alias_exports),
    )


def _extract_decl_name(*, kind: str, rest: str, line_no: int) -> str | None:
    if kind == "instance":
        named = re.match(r"^(?P<name>[A-Za-z0-9_'.]+)\s*:", rest)
        if named is not None:
            return named.group("name")
        return f"_anonymous_instance_L{line_no}"
    match = _SIMPLE_NAME_RE.match(rest)
    if match is None:
        return None
    return match.group("name")


def _split_signature_and_value(
    *,
    kind: str,
    short_name: str,
    header: str,
    body: str,
) -> tuple[str | None, str | None]:
    if ":=" in body:
        left, right = body.split(":=", 1)
        return _normalize_signature(kind=kind, short_name=short_name, text=left), (
            f":= {right.strip()}".strip() or None
        )
    if " where" in body:
        left, right = body.split(" where", 1)
        return _normalize_signature(kind=kind, short_name=short_name, text=left), (
            f"where{right}".strip() or None
        )
    return _normalize_signature(kind=kind, short_name=short_name, text=header), None


def _normalize_kind(kind: str) -> str:
    normalized = kind.strip().lower()
    if normalized == "def":
        return "definition"
    return normalized


def _normalize_signature(*, kind: str, short_name: str, text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None
    prefix = re.compile(rf"^\s*{re.escape(kind)}\s+{re.escape(short_name)}\b")
    normalized = prefix.sub("", stripped, count=1).strip()
    return normalized or None


__all__ = ["parse_declarations"]
