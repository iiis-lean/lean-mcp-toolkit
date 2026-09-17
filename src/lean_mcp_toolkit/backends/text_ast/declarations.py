"""Top-level declaration parsing for Lean source text.

This is a toolkit-owned, source-oriented parser. It deliberately reports
command-classification coverage instead of claiming Lean parser or elaborator
fidelity. Consumers that require canonical names, types, or dependencies must
use a Lean-backed backend.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from .comments import mask_comments_and_strings
from .models import (
    ParsedLeanModule,
    TextAstCommandIssue,
    TextAstCoverage,
    TextAstDeclaration,
    TextAstPosition,
)
from .namespace import qualify_name

_DECL_RE = re.compile(
    r"^(?P<kw>theorem|lemma|def|abbrev|instance|axiom|constant|opaque|structure|class|inductive)\b(?P<rest>.*)$"
)
_NAMESPACE_RE = re.compile(r"^namespace\s+(?P<name>[^\s]+)")
_SECTION_RE = re.compile(r"^section(?:\s+(?P<name>[^\s]+))?\b")
_END_RE = re.compile(r"^end(?:\s+(?P<name>[^\s]+))?\b")
_ALIAS_RE = re.compile(r"^alias\s+.+?:=\s+(?P<export>[^\s]+)\s*$")
_IDENT_SEGMENT = r"(?:«[^»\r\n]+»|[^\W\d][\w']*)"
_LEAN_NAME = rf"(?:_root_\.)?{_IDENT_SEGMENT}(?:\.{_IDENT_SEGMENT})*"
_SIMPLE_NAME_RE = re.compile(rf"^(?P<name>{_LEAN_NAME})")
_NAMED_INSTANCE_RE = re.compile(rf"^(?P<name>{_LEAN_NAME})\s*:")
_COMMAND_HEAD_RE = re.compile(r"^(?P<head>#[A-Za-z_][A-Za-z0-9_']*|[A-Za-z_][A-Za-z0-9_']*)")

_DECL_MODIFIERS = frozenset(
    {
        "local",
        "noncomputable",
        "nonrec",
        "partial",
        "private",
        "protected",
        "public",
        "scoped",
        "unsafe",
    }
)
_KNOWN_NON_DECL_COMMANDS = frozenset(
    {
        "add_decl_doc",
        "add_tactic_doc",
        "attribute",
        "builtin_initialize",
        "builtin_macro",
        "builtin_simproc",
        "builtin_tactic",
        "command_elab",
        "declare_syntax_cat",
        "elab",
        "elab_rules",
        "example",
        "export",
        "include",
        "infix",
        "infixl",
        "infixr",
        "initialize",
        "input_file",
        "import",
        "lean_exe",
        "lean_lib",
        "library_facet",
        "macro",
        "macro_rules",
        "meta",
        "module_facet",
        "notation",
        "notation3",
        "omit",
        "open",
        "package",
        "package_facet",
        "postfix",
        "prefix",
        "prelude",
        "register_builtin_option",
        "register_option",
        "recommended_spelling",
        "require",
        "run_tac",
        "script",
        "set_option",
        "simproc",
        "syntax",
        "syntax_cat",
        "tactic",
        "term_elab",
        "universe",
        "universes",
        "variable",
        "variables",
    }
)
_CONTINUATION_HEADS = frozenset({"decreasing_by", "deriving", "termination_by", "where"})


@dataclass(slots=True, frozen=True)
class _PendingDoc:
    text: str
    start_line: int
    end_line: int


@dataclass(slots=True, frozen=True)
class _Scope:
    kind: str
    name: str | None


@dataclass(slots=True, frozen=True)
class _DeclStart:
    full_start_idx: int
    body_start_idx: int
    keyword_column: int
    kind: str
    short_name: str
    full_name: str
    doc: _PendingDoc | None


def parse_declarations(*, text: str, module_dot: str) -> ParsedLeanModule:
    """Parse declarations and report classified source command starts.

    The coverage ratio is not a declaration-recall or semantic-correctness
    score. ``module_dot`` remains accepted for interface compatibility; source
    namespaces, rather than the file name, determine declaration names.
    """

    _ = module_dot
    masked = mask_comments_and_strings(text)
    lines = text.splitlines()
    masked_lines = masked.splitlines()
    comment_masked_lines = mask_comments_and_strings(text, mask_strings=False).splitlines()
    scopes: list[_Scope] = []
    alias_exports: list[str] = []
    pending_doc: _PendingDoc | None = None
    pending_prefix_start: int | None = None
    attribute_depth = 0
    mutual_indent: int | None = None
    mutual_member_indent: int | None = None
    decl_starts: list[_DeclStart] = []
    command_boundaries: list[int] = []
    issues: list[TextAstCommandIssue] = []
    total_commands = 0
    classified_commands = 0

    line_idx = 0
    while line_idx < len(lines):
        original = lines[line_idx]
        masked_line = masked_lines[line_idx] if line_idx < len(masked_lines) else original
        stripped = original.strip()
        masked_stripped = masked_line.strip()
        indent = len(original) - len(original.lstrip())

        candidate_indent = 0 if mutual_indent is None else mutual_member_indent
        can_start_member = mutual_indent is not None and indent > mutual_indent
        at_command_indent = attribute_depth > 0 or (
            indent == 0
            if mutual_indent is None
            else (
                indent == mutual_indent
                or (
                    can_start_member
                    and (candidate_indent is None or indent == candidate_indent)
                )
            )
        )

        if stripped.startswith("/-!") and at_command_indent:
            # Module/section documentation is not part of the preceding proof.
            command_boundaries.append(line_idx)
            pending_doc = None
            pending_prefix_start = None

        if stripped.startswith("/--") and at_command_indent:
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
            if mutual_indent is not None and mutual_member_indent is None:
                mutual_member_indent = indent
            line_idx += 1
            continue

        if not masked_stripped:
            line_idx += 1
            continue

        if not at_command_indent:
            line_idx += 1
            continue

        command_text, command_column, attribute_depth, saw_attribute = _strip_attributes(
            masked_line,
            attribute_depth=attribute_depth,
        )
        if saw_attribute and pending_prefix_start is None:
            pending_prefix_start = line_idx
            if mutual_indent is not None and mutual_member_indent is None:
                mutual_member_indent = indent
        if attribute_depth > 0 or not command_text:
            line_idx += 1
            continue

        command_text, modifier_column, saw_modifier = _strip_modifiers(command_text)
        command_column += modifier_column
        if not command_text:
            if saw_modifier and pending_prefix_start is None:
                pending_prefix_start = line_idx
            line_idx += 1
            continue

        head = _command_head(command_text)
        if (
            head in _CONTINUATION_HEADS
            or command_text.startswith(("|", ":=", "=>"))
            or command_text[:1] in "()[]{}.,"
        ):
            pending_doc = None
            pending_prefix_start = None
            line_idx += 1
            continue

        end_match = _END_RE.match(command_text)
        if mutual_indent is not None and indent == mutual_indent and end_match is not None:
            boundary = _command_boundary(pending_doc, pending_prefix_start, line_idx)
            command_boundaries.append(boundary)
            total_commands += 1
            classified_commands += 1
            mutual_indent = None
            mutual_member_indent = None
            pending_doc = None
            pending_prefix_start = None
            line_idx += 1
            continue

        if mutual_indent is not None and indent == mutual_indent:
            boundary = _command_boundary(pending_doc, pending_prefix_start, line_idx)
            command_boundaries.append(boundary)
            total_commands += 1
            issues.append(_issue(line_idx, command_column, command_text))
            pending_doc = None
            pending_prefix_start = None
            line_idx += 1
            continue

        if mutual_indent is not None and mutual_member_indent is None:
            mutual_member_indent = indent

        boundary = _command_boundary(pending_doc, pending_prefix_start, line_idx)
        decl_match = _DECL_RE.match(command_text)
        if decl_match is not None:
            kind = decl_match.group("kw").lower()
            short_name = _extract_decl_name(
                kind=kind,
                rest=decl_match.group("rest").strip(),
                line_no=line_idx + 1,
            )
            command_boundaries.append(boundary)
            total_commands += 1
            if short_name is None:
                issues.append(_issue(line_idx, command_column, command_text))
            else:
                classified_commands += 1
                full_name = qualify_name(
                    namespace_stack=tuple(
                        scope.name
                        for scope in scopes
                        if scope.kind == "namespace" and scope.name is not None
                    ),
                    raw_name=short_name,
                )
                decl_starts.append(
                    _DeclStart(
                        full_start_idx=boundary,
                        body_start_idx=line_idx,
                        keyword_column=command_column,
                        kind=kind,
                        short_name=short_name,
                        full_name=full_name,
                        doc=pending_doc,
                    )
                )
            pending_doc = None
            pending_prefix_start = None
            line_idx += 1
            continue

        namespace_match = _NAMESPACE_RE.match(command_text)
        section_match = _SECTION_RE.match(command_text)
        alias_match = _ALIAS_RE.match(command_text)
        is_mutual = command_text == "mutual" or command_text.startswith("mutual ")

        command_boundaries.append(boundary)
        total_commands += 1
        if namespace_match is not None:
            classified_commands += 1
            scopes.append(_Scope("namespace", namespace_match.group("name")))
        elif section_match is not None:
            classified_commands += 1
            scopes.append(_Scope("section", section_match.group("name")))
        elif end_match is not None:
            classified_commands += 1
            _close_scope(scopes, end_match.group("name"))
        elif alias_match is not None:
            classified_commands += 1
            export = alias_match.group("export").strip()
            if export and export not in alias_exports:
                alias_exports.append(export)
        elif is_mutual:
            classified_commands += 1
            mutual_indent = indent
            mutual_member_indent = None
        elif head in _KNOWN_NON_DECL_COMMANDS or head.startswith("#"):
            classified_commands += 1
        else:
            issues.append(_issue(line_idx, command_column, command_text))

        pending_doc = None
        pending_prefix_start = None
        line_idx += 1

    declarations: list[TextAstDeclaration] = []
    sorted_boundaries = sorted(set(command_boundaries))
    for decl in decl_starts:
        next_start = len(lines)
        for boundary_idx in sorted_boundaries:
            if boundary_idx > decl.body_start_idx:
                next_start = boundary_idx
                break
        end_exclusive = next_start
        while end_exclusive > decl.body_start_idx and not comment_masked_lines[end_exclusive - 1].strip():
            end_exclusive -= 1

        end_line_idx = max(decl.body_start_idx, end_exclusive - 1)
        end_col = len(comment_masked_lines[end_line_idx].rstrip())
        declaration_lines = lines[decl.body_start_idx:end_exclusive]
        if declaration_lines:
            declaration_lines[-1] = declaration_lines[-1][:end_col]
        if declaration_lines:
            declaration_lines[0] = declaration_lines[0][decl.keyword_column:]
        declaration_text = "\n".join(declaration_lines).rstrip()
        block_lines = lines[decl.full_start_idx:end_exclusive]
        if block_lines:
            block_lines[-1] = block_lines[-1][:end_col]
        block_text = "\n".join(block_lines).rstrip()
        header = declaration_lines[0].strip() if declaration_lines else ""
        signature, value = _split_signature_and_value(
            kind=decl.kind,
            short_name=decl.short_name,
            header=header,
            body=declaration_text,
        )
        declarations.append(
            TextAstDeclaration(
                name=decl.full_name,
                short_name=decl.short_name,
                kind=_normalize_kind(decl.kind),
                signature=signature,
                value=value,
                full_declaration=block_text or None,
                docstring=(decl.doc.text if decl.doc is not None else None),
                decl_start_pos=TextAstPosition(line=decl.full_start_idx + 1, column=0),
                decl_end_pos=TextAstPosition(line=end_line_idx + 1, column=end_col),
                doc_start_pos=(
                    TextAstPosition(line=decl.doc.start_line, column=0)
                    if decl.doc is not None
                    else None
                ),
                doc_end_pos=(
                    TextAstPosition(
                        line=decl.doc.end_line,
                        column=(
                            len(lines[decl.doc.end_line - 1])
                            if 0 <= decl.doc.end_line - 1 < len(lines)
                            else 0
                        ),
                    )
                    if decl.doc is not None
                    else None
                ),
            )
        )

    return ParsedLeanModule(
        declarations=tuple(declarations),
        alias_exports=tuple(alias_exports),
        coverage=TextAstCoverage(
            total_top_level_commands=total_commands,
            classified_top_level_commands=classified_commands,
            unrecognized_commands=tuple(issues),
        ),
    )


def _strip_attributes(line: str, *, attribute_depth: int) -> tuple[str, int, int, bool]:
    """Remove leading ``@[...]`` blocks and preserve the remaining column."""

    pos = len(line) - len(line.lstrip())
    saw_attribute = attribute_depth > 0
    while True:
        if attribute_depth == 0:
            while pos < len(line) and line[pos].isspace():
                pos += 1
            if not line.startswith("@[", pos):
                return line[pos:].strip(), pos, 0, saw_attribute
            saw_attribute = True
            attribute_depth = 1
            pos += 2
        while pos < len(line) and attribute_depth > 0:
            if line[pos] == "[":
                attribute_depth += 1
            elif line[pos] == "]":
                attribute_depth -= 1
            pos += 1
        if attribute_depth > 0:
            return "", pos, attribute_depth, saw_attribute


def _strip_modifiers(text: str) -> tuple[str, int, bool]:
    pos = 0
    saw_modifier = False
    while True:
        match = re.match(r"[A-Za-z_][A-Za-z0-9_']*\b", text[pos:])
        if match is None or match.group(0) not in _DECL_MODIFIERS:
            break
        saw_modifier = True
        pos += match.end()
        while pos < len(text) and text[pos].isspace():
            pos += 1
    return text[pos:], pos, saw_modifier


def _command_boundary(
    pending_doc: _PendingDoc | None,
    pending_prefix_start: int | None,
    line_idx: int,
) -> int:
    if pending_doc is not None:
        return pending_doc.start_line - 1
    if pending_prefix_start is not None:
        return pending_prefix_start
    return line_idx


def _command_head(text: str) -> str:
    match = _COMMAND_HEAD_RE.match(text)
    return match.group("head") if match is not None else text[:1]


def _issue(line_idx: int, column: int, command_text: str) -> TextAstCommandIssue:
    return TextAstCommandIssue(
        line=line_idx + 1,
        column=column,
        head=_command_head(command_text),
        source=command_text[:240],
    )


def _close_scope(scopes: list[_Scope], end_name: str | None) -> None:
    if not scopes:
        return
    if not end_name:
        scopes.pop()
        return
    for idx in range(len(scopes) - 1, -1, -1):
        if scopes[idx].name == end_name:
            del scopes[idx:]
            return


def _extract_decl_name(*, kind: str, rest: str, line_no: int) -> str | None:
    if kind == "instance":
        named = _NAMED_INSTANCE_RE.match(rest)
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
    # Split only at a top-level delimiter and keep the exact original suffix.
    # Normalizing whitespace here makes source range recovery fail for term
    # proofs whose body starts on the next line.
    masked = mask_comments_and_strings(body)
    depth = 0
    quoted_name = False
    pending_bindings = 0
    for index, char in enumerate(masked):
        if char == '«':
            quoted_name = True
        if quoted_name:
            if char == '»':
                quoted_name = False
            continue
        if char in '([{⦃':
            depth += 1
        elif char in ')]}⦄':
            depth = max(0, depth - 1)
        if depth:
            continue
        if (char.isalpha() and (index == 0 or not (masked[index - 1].isalnum() or masked[index - 1] == '_'))
                and re.match(r'(?:letI|let|haveI|have)\b', masked[index:])):
            pending_bindings += 1
        if masked.startswith(':=', index) and pending_bindings:
            pending_bindings -= 1
            continue
        is_where = (masked.startswith('where', index)
                    and (index == 0 or masked[index - 1].isspace())
                    and (index + 5 == len(masked) or masked[index + 5].isspace()))
        line_start = masked.rfind('\n', 0, index) + 1 if char == '|' else 0
        is_equation = (kind in {'def', 'abbrev', 'instance', 'theorem', 'lemma'} and char == '|'
                       and index + 1 < len(masked) and masked[index + 1].isspace()
                       and not masked[line_start:index].strip()
                       and re.match(r'\|\s+[^|\n]*=>', masked[index:]) is not None
                       and re.search(r'\bmatch\b', masked[:index]) is None)
        if masked.startswith(':=', index) or is_where or is_equation:
            return (_normalize_signature(kind=kind, short_name=short_name, text=body[:index]),
                    body[index:].rstrip())
    return _normalize_signature(kind=kind, short_name=short_name, text=body), None


def _normalize_kind(kind: str) -> str:
    normalized = kind.strip().lower()
    if normalized == "def":
        return "definition"
    return normalized


def _normalize_signature(*, kind: str, short_name: str, text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None
    prefix = re.compile(
        rf"^\s*{re.escape(kind)}\s+{re.escape(short_name)}(?=\s|\(|\{{|\[|:|$)"
    )
    normalized = prefix.sub("", stripped, count=1).strip()
    return normalized or None


__all__ = ["parse_declarations"]
