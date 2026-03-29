"""Tiny helpers for line/index conversions."""

from __future__ import annotations

from bisect import bisect_right

from .models import TextAstPosition


def line_offsets(text: str) -> list[int]:
    offsets = [0]
    for idx, ch in enumerate(text):
        if ch == "\n":
            offsets.append(idx + 1)
    return offsets


def index_to_position(*, offsets: list[int], index: int) -> TextAstPosition:
    line_idx = bisect_right(offsets, index) - 1
    line_start = offsets[max(0, line_idx)]
    return TextAstPosition(line=line_idx + 1, column=max(0, index - line_start))


__all__ = ["index_to_position", "line_offsets"]
