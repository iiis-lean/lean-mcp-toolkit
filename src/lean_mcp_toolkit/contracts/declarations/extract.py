"""Contracts for declarations.extract."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict


@dataclass(frozen=True)
class DeclarationExtractRequest(DictModel):
    project_root: str | None = None
    target: str = ""

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DeclarationExtractRequest":
        return cls(
            project_root=(str(data["project_root"]) if data.get("project_root") is not None else None),
            target=str(data.get("target") or ""),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "target": self.target,
        }


@dataclass(frozen=True)
class DeclarationPosition(DictModel):
    line: int
    column: int

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DeclarationPosition":
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
class DeclarationItem(DictModel):
    name: str
    kind: str | None = None
    signature: str | None = None
    value: str | None = None
    full_declaration: str | None = None
    docstring: str | None = None
    decl_start_pos: DeclarationPosition | None = None
    decl_end_pos: DeclarationPosition | None = None
    doc_start_pos: DeclarationPosition | None = None
    doc_end_pos: DeclarationPosition | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DeclarationItem":
        decl_start_pos = (
            DeclarationPosition.from_dict(data["decl_start_pos"])
            if isinstance(data.get("decl_start_pos"), dict)
            else None
        )
        decl_end_pos = (
            DeclarationPosition.from_dict(data["decl_end_pos"])
            if isinstance(data.get("decl_end_pos"), dict)
            else None
        )
        doc_start_pos = (
            DeclarationPosition.from_dict(data["doc_start_pos"])
            if isinstance(data.get("doc_start_pos"), dict)
            else None
        )
        doc_end_pos = (
            DeclarationPosition.from_dict(data["doc_end_pos"])
            if isinstance(data.get("doc_end_pos"), dict)
            else None
        )
        return cls(
            name=str(data.get("name") or ""),
            kind=(str(data["kind"]) if data.get("kind") is not None else None),
            signature=(str(data["signature"]) if data.get("signature") is not None else None),
            value=(str(data["value"]) if data.get("value") is not None else None),
            full_declaration=(
                str(data["full_declaration"])
                if data.get("full_declaration") is not None
                else None
            ),
            docstring=(str(data["docstring"]) if data.get("docstring") is not None else None),
            decl_start_pos=decl_start_pos,
            decl_end_pos=decl_end_pos,
            doc_start_pos=doc_start_pos,
            doc_end_pos=doc_end_pos,
        )

    def to_dict(self) -> JsonDict:
        return {
            "name": self.name,
            "kind": self.kind,
            "signature": self.signature,
            "value": self.value,
            "full_declaration": self.full_declaration,
            "docstring": self.docstring,
            "decl_start_pos": (
                self.decl_start_pos.to_dict() if self.decl_start_pos is not None else None
            ),
            "decl_end_pos": (
                self.decl_end_pos.to_dict() if self.decl_end_pos is not None else None
            ),
            "doc_start_pos": (
                self.doc_start_pos.to_dict() if self.doc_start_pos is not None else None
            ),
            "doc_end_pos": (
                self.doc_end_pos.to_dict() if self.doc_end_pos is not None else None
            ),
        }

    def to_markdown(self) -> str:
        base = f"- `{self.name}`"
        if self.kind:
            base += f" ({self.kind})"
        lines = [base]
        if self.signature:
            lines.append(f"  - signature: `{self.signature}`")
        if self.value:
            lines.append(f"  - value: `{self.value}`")
        if self.docstring:
            lines.append("  - docstring: present")
        if self.decl_start_pos and self.decl_end_pos:
            lines.append(
                "  - decl_range: "
                f"`({self.decl_start_pos.line},{self.decl_start_pos.column}) -> "
                f"({self.decl_end_pos.line},{self.decl_end_pos.column})`"
            )
        if self.doc_start_pos and self.doc_end_pos:
            lines.append(
                "  - doc_range: "
                f"`({self.doc_start_pos.line},{self.doc_start_pos.column}) -> "
                f"({self.doc_end_pos.line},{self.doc_end_pos.column})`"
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class DeclarationExtractResponse(DictModel):
    success: bool
    error_message: str | None = None
    total_declarations: int = 0
    declarations: tuple[DeclarationItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "DeclarationExtractResponse":
        raw_decls = data.get("declarations")
        parsed: list[DeclarationItem] = []
        if isinstance(raw_decls, list):
            for item in raw_decls:
                if isinstance(item, dict):
                    parsed.append(DeclarationItem.from_dict(item))
        total = data.get("total_declarations")
        parsed_total = int(total) if isinstance(total, (int, str)) and str(total).strip() else len(parsed)
        return cls(
            success=bool(data.get("success", False)),
            error_message=(str(data["error_message"]) if data.get("error_message") is not None else None),
            total_declarations=parsed_total,
            declarations=tuple(parsed),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "total_declarations": self.total_declarations,
            "declarations": [item.to_dict() for item in self.declarations],
        }

    def to_markdown(self, *, title: str | None = "Declarations", title_level: int = 2) -> str:
        chunks: list[str] = []
        if title:
            chunks.append(f"{'#' * max(1, title_level)} {title}")
        chunks.append(f"- success: `{str(self.success).lower()}`")
        chunks.append(f"- total_declarations: `{self.total_declarations}`")
        if self.error_message:
            chunks.append(f"- error_message: {self.error_message}")
        if self.declarations:
            chunks.append("")
            chunks.extend(item.to_markdown() for item in self.declarations)
        return "\n".join(chunks)
