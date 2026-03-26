"""Lean proof profiling helpers for lsp_heavy."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import tempfile

from ...contracts.lsp_heavy import ProfileCategory, ProfileLine

_TRACE_RE = re.compile(r"^(\s*)\[([^\]]+)\]\s+\[([\d.]+)\]\s+(.+)$")
_CUMULATIVE_RE = re.compile(r"^\s+(\S+(?:\s+\S+)*)\s+([\d.]+)(ms|s)$")
_DECL_RE = re.compile(r"^\s*(?:private\s+)?(theorem|lemma|def)\s+(\S+)")
_HEADER_RE = re.compile(r"^(import|open|set_option|universe|variable)\s")
_SKIP_CATEGORIES = {"import", "initialization", "parsing", "interpretation", "linting"}


@dataclass(slots=True, frozen=True)
class ProofProfileData:
    theorem_name: str
    total_ms: float
    lines: tuple[ProfileLine, ...]
    categories: tuple[ProfileCategory, ...]


def profile_theorem(
    *,
    file_path: Path,
    theorem_line: int,
    project_root: Path,
    timeout_seconds: int,
    top_n: int,
) -> ProofProfileData:
    lines = file_path.read_text(encoding="utf-8").splitlines()
    if not (0 < theorem_line <= len(lines)):
        raise ValueError(f"line {theorem_line} out of range")

    source, theorem_name, source_decl_start = _extract_theorem_source(lines, theorem_line)
    source_lines = source.splitlines()
    line_offset = theorem_line - source_decl_start
    proof_start = _find_proof_start(source_lines)
    proof_items = _build_proof_items(source_lines, proof_start)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".lean",
        dir=project_root,
        delete=False,
        encoding="utf-8",
    ) as handle:
        handle.write(source)
        temp_path = Path(handle.name)

    try:
        output = _run_lean_profile(
            file_path=temp_path,
            project_root=project_root,
            timeout_seconds=timeout_seconds,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    traces, cumulative = _parse_output(output)
    line_times, total_ms = _extract_line_times(traces, theorem_name, proof_items)
    top_lines = sorted(
        [
            (line_no, ms)
            for line_no, ms in line_times.items()
            if total_ms <= 0 or ms >= total_ms * 0.01
        ],
        key=lambda item: -item[1],
    )[:top_n]

    return ProofProfileData(
        theorem_name=theorem_name,
        total_ms=round(total_ms, 1),
        lines=tuple(
            ProfileLine(
                line=line_no + line_offset,
                ms=round(ms, 1),
                text=(
                    source_lines[line_no - 1].strip()[:120]
                    if 0 < line_no <= len(source_lines)
                    else ""
                ),
            )
            for line_no, ms in top_lines
        ),
        categories=tuple(_filter_categories(cumulative)),
    )


def _run_lean_profile(
    *,
    file_path: Path,
    project_root: Path,
    timeout_seconds: int,
) -> str:
    completed = subprocess.run(
        [
            "lake",
            "env",
            "lean",
            "--profile",
            "-Dtrace.profiler=true",
            "-Dtrace.profiler.threshold=0",
            str(file_path.resolve()),
        ],
        cwd=str(project_root.resolve()),
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        raise RuntimeError(
            output.strip() or f"lean profile failed with exit code {completed.returncode}"
        )
    return output


def _find_header_end(lines: list[str]) -> int:
    header_end = 0
    in_block = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if "/-" in line:
            in_block = True
        if "-/" in line:
            in_block = False
        if in_block or not stripped or stripped.startswith("--") or _HEADER_RE.match(line):
            header_end = index + 1
        elif stripped.startswith(("namespace", "section")):
            header_end = index + 1
        elif _DECL_RE.match(line) or stripped.startswith(("@[", "private ", "protected ")):
            break
        else:
            header_end = index + 1
    return header_end


def _find_theorem_end(lines: list[str], start: int) -> int:
    for index in range(start + 1, len(lines)):
        if _DECL_RE.match(lines[index]):
            return index
    return len(lines)


def _extract_theorem_source(lines: list[str], target_line: int) -> tuple[str, str, int]:
    match = _DECL_RE.match(lines[target_line - 1])
    if not match:
        raise ValueError(f"no theorem/lemma/def at line {target_line}")
    header_end = _find_header_end(lines)
    theorem_end = _find_theorem_end(lines, target_line - 1)
    header = "\n".join(lines[:header_end])
    theorem = "\n".join(lines[target_line - 1 : theorem_end])
    return f"{header}\n\n{theorem}\n", match.group(2), header_end + 2


def _find_proof_start(source_lines: list[str]) -> int:
    for index, line in enumerate(source_lines):
        if ":= by" in line or line.rstrip().endswith(" by"):
            return index + 1
    raise ValueError("no `by` proof found in theorem")


def _build_proof_items(source_lines: list[str], proof_start: int) -> list[tuple[int, str, bool]]:
    items: list[tuple[int, str, bool]] = []
    for index in range(proof_start, len(source_lines)):
        stripped = source_lines[index].strip()
        if stripped and not stripped.startswith("--"):
            is_bullet = stripped[0] in "·*-"
            items.append((index + 1, stripped.lstrip("·*- \t"), is_bullet))
    return items


def _parse_output(output: str) -> tuple[list[tuple[int, str, float, str]], dict[str, float]]:
    traces: list[tuple[int, str, float, str]] = []
    cumulative: dict[str, float] = {}
    in_cumulative = False

    for line in output.splitlines():
        if "cumulative profiling times:" in line:
            in_cumulative = True
            continue
        if in_cumulative:
            match = _CUMULATIVE_RE.match(line)
            if match:
                category, value, unit = match.groups()
                cumulative[category] = float(value) * (1000 if unit == "s" else 1)
            continue
        match = _TRACE_RE.match(line)
        if match:
            indent, cls, time_s, msg = match.groups()
            traces.append((len(indent) // 2, cls, float(time_s) * 1000, msg))
    return traces, cumulative


def _match_line(
    tactic: str,
    is_bullet: bool,
    proof_items: list[tuple[int, str, bool]],
    used: set[int],
) -> int | None:
    for line_no, content, source_is_bullet in proof_items:
        if line_no in used:
            continue
        if is_bullet and source_is_bullet:
            return line_no
        if not is_bullet and content and (
            tactic.startswith(content[:25]) or content.startswith(tactic[:25])
        ):
            return line_no
    return None


def _extract_line_times(
    traces: list[tuple[int, str, float, str]],
    theorem_name: str,
    proof_items: list[tuple[int, str, bool]],
) -> tuple[dict[int, float], float]:
    line_times: dict[int, float] = defaultdict(float)
    total = 0.0
    value_depth = 0
    in_value = False
    tactic_depth: int | None = None
    name_re = re.compile(rf"\b{re.escape(theorem_name)}\b")
    used: set[int] = set()

    for depth, cls, ms, msg in traces:
        if cls == "Elab.definition.value" and name_re.search(msg):
            in_value = True
            value_depth = depth
            total = max(total, ms)
            continue
        if cls == "Elab.async" and f"proof of {theorem_name}" in msg:
            total = max(total, ms)
            continue
        if not in_value:
            continue
        if depth <= value_depth:
            break
        if cls != "Elab.step" or msg.startswith("expected type:"):
            continue
        tactic_depth = tactic_depth or depth
        if depth != tactic_depth:
            continue
        tactic = msg.split("\n", 1)[0].strip().lstrip("·*- \t")
        matched = _match_line(tactic, not bool(tactic), proof_items, used)
        if matched is None:
            continue
        line_times[matched] += ms
        used.add(matched)
    return dict(line_times), total


def _filter_categories(cumulative: dict[str, float]) -> list[ProfileCategory]:
    return [
        ProfileCategory(name=name, ms=round(ms, 1))
        for name, ms in sorted(cumulative.items(), key=lambda item: -item[1])
        if name not in _SKIP_CATEGORIES and ms >= 1.0
    ]
