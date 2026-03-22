"""Contracts for search.local_decl.search."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool, to_int


@dataclass(slots=True, frozen=True)
class LocalDeclSearchRequest(DictModel):
    query: str = ""
    project_root: str | None = None
    limit: int | None = None
    include_dependencies: bool | None = None
    include_stdlib: bool | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalDeclSearchRequest":
        return cls(
            query=str(data.get("query") or ""),
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            limit=to_int(data.get("limit"), default=None),
            include_dependencies=(
                to_bool(data.get("include_dependencies"), default=True)
                if "include_dependencies" in data
                else None
            ),
            include_stdlib=(
                to_bool(data.get("include_stdlib"), default=True)
                if "include_stdlib" in data
                else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "query": self.query,
            "project_root": self.project_root,
            "limit": self.limit,
            "include_dependencies": self.include_dependencies,
            "include_stdlib": self.include_stdlib,
        }


@dataclass(slots=True, frozen=True)
class LocalDeclSearchItem(DictModel):
    name: str
    kind: str
    file: str
    origin: str

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalDeclSearchItem":
        return cls(
            name=str(data.get("name") or ""),
            kind=str(data.get("kind") or ""),
            file=str(data.get("file") or ""),
            origin=str(data.get("origin") or "project"),
        )

    def to_dict(self) -> JsonDict:
        return {
            "name": self.name,
            "kind": self.kind,
            "file": self.file,
            "origin": self.origin,
        }


@dataclass(slots=True, frozen=True)
class LocalDeclSearchResponse(DictModel):
    query: str
    count: int
    items: tuple[LocalDeclSearchItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LocalDeclSearchResponse":
        parsed: list[LocalDeclSearchItem] = []
        raw = data.get("items")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    parsed.append(LocalDeclSearchItem.from_dict(item))
        return cls(
            query=str(data.get("query") or ""),
            count=(to_int(data.get("count"), default=None) or len(parsed)),
            items=tuple(parsed),
        )

    def to_dict(self) -> JsonDict:
        return {
            "query": self.query,
            "count": self.count,
            "items": [item.to_dict() for item in self.items],
        }
