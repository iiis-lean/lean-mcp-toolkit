"""Shared diagnostics-level contract models."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict


@dataclass(frozen=True)
class Position(DictModel):
    line: int
    column: int

    @classmethod
    def from_dict(cls, data: JsonDict) -> "Position":
        return cls(
            line=int(data.get("line", 0) or 0),
            column=int(data.get("column", 0) or 0),
        )

    def to_dict(self) -> JsonDict:
        return {"line": self.line, "column": self.column}


@dataclass(frozen=True)
class DiagnosticItem(DictModel):
    severity: str
    pos: Position | None
    endPos: Position | None
    kind: str | None
    data: str
    fileName: str | None
    content: str | None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DiagnosticItem":
        raw_pos = data.get("pos")
        raw_end = data.get("endPos")
        return cls(
            severity=str(data.get("severity") or ""),
            pos=Position.from_dict(raw_pos) if isinstance(raw_pos, dict) else None,
            endPos=Position.from_dict(raw_end) if isinstance(raw_end, dict) else None,
            kind=(str(data["kind"]) if data.get("kind") is not None else None),
            data=str(data.get("data") or ""),
            fileName=(str(data["fileName"]) if data.get("fileName") is not None else None),
            content=(str(data["content"]) if data.get("content") is not None else None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "severity": self.severity,
            "pos": self.pos.to_dict() if self.pos else None,
            "endPos": self.endPos.to_dict() if self.endPos else None,
            "kind": self.kind,
            "data": self.data,
            "fileName": self.fileName,
            "content": self.content,
        }

    def to_markdown(self) -> str:
        severity = (self.severity or "error").strip().lower() or "error"
        location = _display_file_name(self.fileName)
        if self.pos is not None:
            if location:
                location = f"{location}:{self.pos.line}:{self.pos.column}"
            else:
                location = f"{self.pos.line}:{self.pos.column}"

        if location:
            line = f"{severity}: {location}: {self.data}".rstrip()
        else:
            line = f"{severity}: {self.data}".rstrip()
        if not self.content:
            return line
        return f"{line}\n\n```lean\n{self.content}\n```"


def _display_file_name(file_name: str | None) -> str | None:
    if not file_name:
        return None
    name = file_name.strip()
    if not name:
        return None
    if "/" in name or "\\" in name or name.endswith(".lean"):
        return name
    if "." in name:
        return f"{name.replace('.', '/')}.lean"
    return name


@dataclass(frozen=True)
class FileDiagnostics(DictModel):
    file: str
    success: bool
    items: tuple[DiagnosticItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "FileDiagnostics":
        raw_items = data.get("items")
        parsed_items: list[DiagnosticItem] = []
        if isinstance(raw_items, list):
            for item in raw_items:
                if isinstance(item, dict):
                    parsed_items.append(DiagnosticItem.from_dict(item))
        return cls(
            file=str(data.get("file") or ""),
            success=bool(data.get("success", False)),
            items=tuple(parsed_items),
        )

    def to_dict(self) -> JsonDict:
        return {
            "file": self.file,
            "success": self.success,
            "items": [item.to_dict() for item in self.items],
        }

    def to_markdown(self, *, title_level: int = 3) -> str:
        title = f"{'#' * max(1, title_level)} {self.file} ({'OK' if self.success else 'FAILED'})"
        if not self.items:
            return f"{title}\n\n- No diagnostics."
        body = "\n".join(item.to_markdown() for item in self.items)
        return f"{title}\n\n{body}"
