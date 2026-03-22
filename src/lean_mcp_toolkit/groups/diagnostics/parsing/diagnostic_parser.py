"""Parse structured diagnostics from Lean JSON output."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ....backends.lean.path import LeanPath
from ....contracts.diagnostics import DiagnosticItem, Position


@dataclass(slots=True)
class LeanDiagnosticParser:
    """Parse newline-delimited JSON diagnostics from Lean tools."""

    def parse_text(
        self,
        *,
        text: str,
        project_root: Path,
        fallback_module: LeanPath | None,
    ) -> tuple[DiagnosticItem, ...]:
        items: list[DiagnosticItem] = []
        for line in text.splitlines():
            payload = line.strip()
            if not payload:
                continue
            try:
                node = json.loads(payload)
            except json.JSONDecodeError:
                continue
            self._collect_items(node=node, out=items, project_root=project_root, fallback=fallback_module)
        return tuple(items)

    def _collect_items(
        self,
        *,
        node: Any,
        out: list[DiagnosticItem],
        project_root: Path,
        fallback: LeanPath | None,
    ) -> None:
        if isinstance(node, list):
            for item in node:
                self._collect_items(node=item, out=out, project_root=project_root, fallback=fallback)
            return

        if not isinstance(node, dict):
            return

        messages = node.get("messages")
        if isinstance(messages, list):
            self._collect_items(node=messages, out=out, project_root=project_root, fallback=fallback)

        if not self._looks_like_message(node):
            return

        severity = str(node.get("severity") or "error")
        data_text = str(node.get("data") or node.get("message") or "")
        kind = str(node["kind"]) if node.get("kind") is not None else None
        pos = self._parse_position(node.get("pos") or node.get("start_pos"))
        end_pos = self._parse_position(node.get("endPos") or node.get("end_pos"))
        file_name = self._normalize_file_name(
            raw_file_name=node.get("fileName") or node.get("file_name"),
            project_root=project_root,
            fallback=fallback,
        )

        out.append(
            DiagnosticItem(
                severity=severity,
                pos=pos,
                endPos=end_pos,
                kind=kind,
                data=data_text,
                fileName=file_name,
                content=None,
            )
        )

    def _looks_like_message(self, node: dict[str, Any]) -> bool:
        if "severity" in node and ("data" in node or "message" in node):
            return True
        if "severity" in node and "pos" in node:
            return True
        return False

    def _parse_position(self, raw: Any) -> Position | None:
        if not isinstance(raw, dict):
            return None
        if raw.get("line") is None:
            return None
        line = int(raw.get("line") or 0)
        col = int(raw.get("column") or 0)
        if line <= 0:
            return None
        return Position(line=line, column=max(0, col))

    def _normalize_file_name(
        self,
        *,
        raw_file_name: Any,
        project_root: Path,
        fallback: LeanPath | None,
    ) -> str | None:
        if raw_file_name is None:
            return fallback.dot if fallback is not None else None

        text = str(raw_file_name).strip()
        if not text:
            return fallback.dot if fallback is not None else None

        candidate = Path(text)
        try:
            if candidate.is_absolute():
                return LeanPath.from_abs_file(candidate, project_root).dot
            if text.endswith(".lean") or "/" in text:
                return LeanPath.from_rel_file(text).dot
            return LeanPath.from_dot(text).dot
        except Exception:
            return fallback.dot if fallback is not None else None
