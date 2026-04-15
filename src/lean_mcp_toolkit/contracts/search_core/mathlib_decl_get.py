"""Contracts for lean_explore.get."""

from __future__ import annotations

from dataclasses import dataclass

from ..base import DictModel, JsonDict, to_bool
from .mathlib_decl_find import MathlibDeclSummaryItem


@dataclass(frozen=True)
class MathlibDeclGetRequest(DictModel):
    declaration_id: int = 0
    include_module: bool = True
    include_docstring: bool = True
    include_source_text: bool = True
    include_source_link: bool = True
    include_dependencies: bool = True
    include_informalization: bool = True

    @classmethod
    def from_dict(cls, data: JsonDict) -> "MathlibDeclGetRequest":
        return cls(
            declaration_id=int(data.get("declaration_id") or 0),
            include_module=to_bool(data.get("include_module"), default=True),
            include_docstring=to_bool(data.get("include_docstring"), default=True),
            include_source_text=to_bool(data.get("include_source_text"), default=True),
            include_source_link=to_bool(data.get("include_source_link"), default=True),
            include_dependencies=to_bool(data.get("include_dependencies"), default=True),
            include_informalization=to_bool(
                data.get("include_informalization"),
                default=True,
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "declaration_id": self.declaration_id,
            "include_module": self.include_module,
            "include_docstring": self.include_docstring,
            "include_source_text": self.include_source_text,
            "include_source_link": self.include_source_link,
            "include_dependencies": self.include_dependencies,
            "include_informalization": self.include_informalization,
        }


@dataclass(frozen=True)
class MathlibDeclGetResponse(DictModel):
    found: bool
    item: MathlibDeclSummaryItem | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "MathlibDeclGetResponse":
        raw_item = data.get("item")
        return cls(
            found=bool(data.get("found", False)),
            item=(MathlibDeclSummaryItem.from_dict(raw_item) if isinstance(raw_item, dict) else None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "found": self.found,
            "item": self.item.to_dict() if self.item is not None else None,
        }
