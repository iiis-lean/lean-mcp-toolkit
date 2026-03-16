"""Source context extraction for diagnostics content field."""

from __future__ import annotations

from dataclasses import dataclass

from ....contracts.diagnostics import Position


@dataclass(slots=True)
class ContextExtractor:
    """Extract context windows around diagnostic positions.

    This extractor intentionally does not add visual markers.
    """

    def extract(
        self,
        *,
        source_text: str,
        start_pos: Position | None,
        end_pos: Position | None,
        context_lines: int,
    ) -> str | None:
        if not source_text or start_pos is None:
            return None

        lines = source_text.split("\n")
        if not lines:
            return None

        start_line_idx = start_pos.line - 1
        if start_line_idx < 0 or start_line_idx >= len(lines):
            return None

        end_line_idx = start_line_idx
        if end_pos is not None:
            end_line_idx = max(start_line_idx, end_pos.line - 1)
            end_line_idx = min(end_line_idx, len(lines) - 1)

        head = max(0, start_line_idx - max(0, context_lines))
        tail = min(len(lines) - 1, end_line_idx + max(0, context_lines))

        snippet = "\n".join(lines[head : tail + 1]).strip("\n")
        return snippet or None
