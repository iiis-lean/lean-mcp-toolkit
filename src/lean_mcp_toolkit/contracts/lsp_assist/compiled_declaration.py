"""Contracts for exact compiled declaration inspection."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool


@dataclass(frozen=True)
class CompiledDeclarationTarget(DictModel):
    module: str = ""
    declaration_name: str = ""

    @classmethod
    def from_dict(cls, data: JsonDict) -> "CompiledDeclarationTarget":
        return cls(
            module=str(data.get("module") or ""),
            declaration_name=str(data.get("declaration_name") or ""),
        )

    def to_dict(self) -> JsonDict:
        return {
            "module": self.module,
            "declaration_name": self.declaration_name,
        }


@dataclass(frozen=True)
class CompiledDeclarationResult(DictModel):
    module: str
    declaration_name: str
    success: bool
    error_message: str | None = None
    owner_module: str | None = None
    declaration_kind: str | None = None
    signature: str | None = None
    universe_count: int = 0
    representation: str | None = None
    reference_code: str | None = None
    generation_kind: str | None = None
    generator_declaration: str | None = None
    provenance_error_message: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "CompiledDeclarationResult":
        return cls(
            module=str(data.get("module") or ""),
            declaration_name=str(data.get("declaration_name") or ""),
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"])
                if data.get("error_message") is not None
                else None
            ),
            owner_module=(
                str(data["owner_module"])
                if data.get("owner_module") is not None
                else None
            ),
            declaration_kind=(
                str(data["declaration_kind"])
                if data.get("declaration_kind") is not None
                else None
            ),
            signature=(
                str(data["signature"])
                if data.get("signature") is not None
                else None
            ),
            universe_count=int(data.get("universe_count") or 0),
            representation=(
                str(data["representation"])
                if data.get("representation") is not None
                else None
            ),
            reference_code=(
                str(data["reference_code"])
                if data.get("reference_code") is not None
                else None
            ),
            generation_kind=(
                str(data["generation_kind"])
                if data.get("generation_kind") is not None
                else None
            ),
            generator_declaration=(
                str(data["generator_declaration"])
                if data.get("generator_declaration") is not None
                else None
            ),
            provenance_error_message=(
                str(data["provenance_error_message"])
                if data.get("provenance_error_message") is not None
                else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "module": self.module,
            "declaration_name": self.declaration_name,
            "success": self.success,
            "error_message": self.error_message,
            "owner_module": self.owner_module,
            "declaration_kind": self.declaration_kind,
            "signature": self.signature,
            "universe_count": self.universe_count,
            "representation": self.representation,
            "reference_code": self.reference_code,
            "generation_kind": self.generation_kind,
            "generator_declaration": self.generator_declaration,
            "provenance_error_message": self.provenance_error_message,
        }


@dataclass(frozen=True)
class LspCompiledDeclarationBatchRequest(DictModel):
    project_root: str | None = None
    declarations: tuple[CompiledDeclarationTarget, ...] = field(default_factory=tuple)
    include_to_additive_provenance: bool = False

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspCompiledDeclarationBatchRequest":
        raw_declarations = data.get("declarations")
        declarations: tuple[CompiledDeclarationTarget, ...] = tuple()
        if isinstance(raw_declarations, list):
            if any(not isinstance(item, dict) for item in raw_declarations):
                raise ValueError("declarations items must be objects")
            declarations = tuple(
                CompiledDeclarationTarget.from_dict(item) for item in raw_declarations
            )
        return cls(
            project_root=(
                str(data["project_root"])
                if data.get("project_root") is not None
                else None
            ),
            declarations=declarations,
            include_to_additive_provenance=to_bool(
                data.get("include_to_additive_provenance"),
                default=False,
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "declarations": [item.to_dict() for item in self.declarations],
            "include_to_additive_provenance": self.include_to_additive_provenance,
        }


@dataclass(frozen=True)
class LspCompiledDeclarationBatchResponse(DictModel):
    success: bool
    error_message: str | None = None
    items: tuple[CompiledDeclarationResult, ...] = field(default_factory=tuple)
    count: int = 0
    success_count: int = 0
    failure_count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LspCompiledDeclarationBatchResponse":
        raw_items = data.get("items")
        items = (
            tuple(
                CompiledDeclarationResult.from_dict(item)
                for item in raw_items
                if isinstance(item, dict)
            )
            if isinstance(raw_items, list)
            else tuple()
        )
        success_count = sum(item.success for item in items)
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"])
                if data.get("error_message") is not None
                else None
            ),
            items=items,
            count=int(data.get("count") or len(items)),
            success_count=int(data.get("success_count") or success_count),
            failure_count=int(
                data.get("failure_count") or (len(items) - success_count)
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "items": [item.to_dict() for item in self.items],
            "count": self.count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }
