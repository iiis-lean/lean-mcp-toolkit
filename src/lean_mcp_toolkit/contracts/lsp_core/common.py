"""Common contracts for lsp_core tools."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict


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


@dataclass(frozen=True)
class LspErrorResponse(DictModel):
    success: bool
    error_message: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspErrorResponse":
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
        }


def diagnostics_to_dict(items: tuple[DiagnosticMessage, ...]) -> list[JsonDict]:
    return [item.to_dict() for item in items]


def parse_diagnostics(raw: object) -> tuple[DiagnosticMessage, ...]:
    parsed: list[DiagnosticMessage] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                parsed.append(DiagnosticMessage.from_dict(item))
    return tuple(parsed)


@dataclass(frozen=True)
class OutlineEntry(DictModel):
    name: str
    kind: str
    start_line: int
    end_line: int
    type_signature: str | None = None
    children: tuple["OutlineEntry", ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "OutlineEntry":
        parsed_children: list[OutlineEntry] = []
        raw = data.get("children")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    parsed_children.append(OutlineEntry.from_dict(item))
        return cls(
            name=str(data.get("name") or ""),
            kind=str(data.get("kind") or ""),
            start_line=int(data.get("start_line") or 0),
            end_line=int(data.get("end_line") or 0),
            type_signature=(
                str(data["type_signature"])
                if data.get("type_signature") is not None
                else None
            ),
            children=tuple(parsed_children),
        )

    def to_dict(self) -> JsonDict:
        return {
            "name": self.name,
            "kind": self.kind,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "type_signature": self.type_signature,
            "children": [item.to_dict() for item in self.children],
        }
