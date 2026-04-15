"""Contracts for declarations.locate."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict
from .extract import DeclarationItem, DeclarationPosition


@dataclass(frozen=True)
class DeclarationLocateRequest(DictModel):
    project_root: str | None = None
    source_file: str = ""
    symbol: str = ""
    line: int | None = None
    column: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DeclarationLocateRequest":
        return cls(
            project_root=(str(data["project_root"]) if data.get("project_root") is not None else None),
            source_file=str(data.get("source_file") or ""),
            symbol=str(data.get("symbol") or ""),
            line=(int(data["line"]) if data.get("line") is not None else None),
            column=(int(data["column"]) if data.get("column") is not None else None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "source_file": self.source_file,
            "symbol": self.symbol,
            "line": self.line,
            "column": self.column,
        }


@dataclass(frozen=True)
class DeclarationLocateRange(DictModel):
    start: DeclarationPosition
    end: DeclarationPosition

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DeclarationLocateRange":
        start = data.get("start")
        end = data.get("end")
        if not isinstance(start, dict) or not isinstance(end, dict):
            raise ValueError("locate range requires `start` and `end` objects")
        return cls(
            start=DeclarationPosition.from_dict(start),
            end=DeclarationPosition.from_dict(end),
        )

    def to_dict(self) -> JsonDict:
        return {
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
        }


@dataclass(frozen=True)
class DeclarationLocateResponse(DictModel):
    success: bool
    error_message: str | None = None
    source_pos: DeclarationPosition | None = None
    target_file_path: str | None = None
    target_range: DeclarationLocateRange | None = None
    matched_declaration: DeclarationItem | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DeclarationLocateResponse":
        source_pos_raw = data.get("source_pos")
        target_range_raw = data.get("target_range")
        matched_raw = data.get("matched_declaration")
        return cls(
            success=bool(data.get("success", False)),
            error_message=(str(data["error_message"]) if data.get("error_message") is not None else None),
            source_pos=(
                DeclarationPosition.from_dict(source_pos_raw)
                if isinstance(source_pos_raw, dict)
                else None
            ),
            target_file_path=(
                str(data["target_file_path"])
                if data.get("target_file_path") is not None
                else None
            ),
            target_range=(
                DeclarationLocateRange.from_dict(target_range_raw)
                if isinstance(target_range_raw, dict)
                else None
            ),
            matched_declaration=(
                DeclarationItem.from_dict(matched_raw)
                if isinstance(matched_raw, dict)
                else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "source_pos": self.source_pos.to_dict() if self.source_pos is not None else None,
            "target_file_path": self.target_file_path,
            "target_range": self.target_range.to_dict() if self.target_range is not None else None,
            "matched_declaration": (
                self.matched_declaration.to_dict()
                if self.matched_declaration is not None
                else None
            ),
        }

