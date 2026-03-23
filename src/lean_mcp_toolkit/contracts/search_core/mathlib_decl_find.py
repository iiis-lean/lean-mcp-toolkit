"""Contracts for search.mathlib_decl.find."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool, to_int, to_list_of_str


@dataclass(slots=True, frozen=True)
class MathlibDeclFindRequest(DictModel):
    query: str = ""
    limit: int | None = None
    rerank_top: int | None = None
    packages: tuple[str, ...] | None = None
    include_module: bool = True
    include_docstring: bool = True
    include_source_text: bool = False
    include_source_link: bool = False
    include_dependencies: bool = False
    include_informalization: bool = False

    @classmethod
    def from_dict(cls, data: JsonDict) -> "MathlibDeclFindRequest":
        return cls(
            query=str(data.get("query") or ""),
            limit=to_int(data.get("limit"), default=None),
            rerank_top=to_int(data.get("rerank_top"), default=None),
            packages=(
                tuple(to_list_of_str(data.get("packages")) or ())
                if data.get("packages") is not None
                else None
            ),
            include_module=to_bool(data.get("include_module"), default=True),
            include_docstring=to_bool(data.get("include_docstring"), default=True),
            include_source_text=to_bool(data.get("include_source_text"), default=False),
            include_source_link=to_bool(data.get("include_source_link"), default=False),
            include_dependencies=to_bool(data.get("include_dependencies"), default=False),
            include_informalization=to_bool(
                data.get("include_informalization"),
                default=False,
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "query": self.query,
            "limit": self.limit,
            "rerank_top": self.rerank_top,
            "packages": list(self.packages) if self.packages is not None else None,
            "include_module": self.include_module,
            "include_docstring": self.include_docstring,
            "include_source_text": self.include_source_text,
            "include_source_link": self.include_source_link,
            "include_dependencies": self.include_dependencies,
            "include_informalization": self.include_informalization,
        }


@dataclass(slots=True, frozen=True)
class MathlibDeclSummaryItem(DictModel):
    id: int
    name: str
    module: str | None = None
    docstring: str | None = None
    source_text: str | None = None
    source_link: str | None = None
    dependencies: str | None = None
    informalization: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "MathlibDeclSummaryItem":
        return cls(
            id=int(data.get("id") or 0),
            name=str(data.get("name") or ""),
            module=(str(data["module"]) if data.get("module") is not None else None),
            docstring=(
                str(data["docstring"]) if data.get("docstring") is not None else None
            ),
            source_text=(
                str(data["source_text"])
                if data.get("source_text") is not None
                else None
            ),
            source_link=(
                str(data["source_link"])
                if data.get("source_link") is not None
                else None
            ),
            dependencies=(
                str(data["dependencies"])
                if data.get("dependencies") is not None
                else None
            ),
            informalization=(
                str(data["informalization"])
                if data.get("informalization") is not None
                else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "id": self.id,
            "name": self.name,
            "module": self.module,
            "docstring": self.docstring,
            "source_text": self.source_text,
            "source_link": self.source_link,
            "dependencies": self.dependencies,
            "informalization": self.informalization,
        }


@dataclass(slots=True, frozen=True)
class MathlibDeclFindResponse(DictModel):
    query: str
    count: int
    processing_time_ms: int | None = None
    results: tuple[MathlibDeclSummaryItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "MathlibDeclFindResponse":
        parsed: list[MathlibDeclSummaryItem] = []
        raw = data.get("results")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    parsed.append(MathlibDeclSummaryItem.from_dict(item))
        count = to_int(data.get("count"), default=None)
        return cls(
            query=str(data.get("query") or ""),
            count=(count if count is not None else len(parsed)),
            processing_time_ms=to_int(data.get("processing_time_ms"), default=None),
            results=tuple(parsed),
        )

    def to_dict(self) -> JsonDict:
        return {
            "query": self.query,
            "count": self.count,
            "processing_time_ms": self.processing_time_ms,
            "results": [item.to_dict() for item in self.results],
        }
