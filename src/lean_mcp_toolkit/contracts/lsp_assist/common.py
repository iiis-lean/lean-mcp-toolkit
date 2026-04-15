"""Common contracts for lsp_assist tools."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict


@dataclass(frozen=True)
class Position(DictModel):
    line: int
    column: int

    @classmethod
    def from_dict(cls, data: JsonDict) -> "Position":
        return cls(
            line=int(data.get("line") or 0),
            column=int(data.get("column") or 0),
        )

    def to_dict(self) -> JsonDict:
        return {
            "line": self.line,
            "column": self.column,
        }


@dataclass(frozen=True)
class Range(DictModel):
    start: Position
    end: Position

    @classmethod
    def from_dict(cls, data: JsonDict) -> "Range":
        raw_start = data.get("start")
        raw_end = data.get("end")
        if not isinstance(raw_start, dict) or not isinstance(raw_end, dict):
            raise ValueError("range requires `start` and `end` objects")
        return cls(
            start=Position.from_dict(raw_start),
            end=Position.from_dict(raw_end),
        )

    def to_dict(self) -> JsonDict:
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
        }


@dataclass(frozen=True)
class DiagnosticMessage(DictModel):
    severity: str
    message: str
    line: int
    column: int

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DiagnosticMessage":
        return cls(
            severity=str(data.get("severity") or ""),
            message=str(data.get("message") or ""),
            line=int(data.get("line") or 0),
            column=int(data.get("column") or 0),
        )

    def to_dict(self) -> JsonDict:
        return {
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
            "column": self.column,
        }

