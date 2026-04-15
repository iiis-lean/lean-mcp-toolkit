"""Contracts for proof_search_alt.hammer_premise."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_int


@dataclass(frozen=True)
class ProofSearchAltHammerPremiseRequest(DictModel):
    project_root: str | None = None
    file_path: str = ""
    line: int = 0
    column: int = 0
    num_results: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ProofSearchAltHammerPremiseRequest":
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            file_path=str(data.get("file_path") or ""),
            line=to_int(data.get("line"), default=0) or 0,
            column=to_int(data.get("column"), default=0) or 0,
            num_results=to_int(data.get("num_results"), default=None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "num_results": self.num_results,
        }


@dataclass(frozen=True)
class HammerPremiseItem(DictModel):
    name: str
    raw_payload: JsonDict | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "HammerPremiseItem":
        raw_payload = data.get("raw_payload")
        return cls(
            name=str(data.get("name") or ""),
            raw_payload=dict(raw_payload) if isinstance(raw_payload, dict) else None,
        )


@dataclass(frozen=True)
class ProofSearchAltHammerPremiseResponse(DictModel):
    success: bool
    error_message: str | None
    provider: str = "hammer_premise"
    goal: str | None = None
    backend_mode: str = "remote"
    items: tuple[HammerPremiseItem, ...] = field(default_factory=tuple)
    count: int = 0

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ProofSearchAltHammerPremiseResponse":
        items = tuple(
            HammerPremiseItem.from_dict(item)
            for item in data.get("items", [])
            if isinstance(item, dict)
        )
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            provider=str(data.get("provider") or "hammer_premise"),
            goal=str(data["goal"]) if data.get("goal") is not None else None,
            backend_mode=str(data.get("backend_mode") or "remote"),
            items=items,
            count=to_int(data.get("count"), default=len(items)) or len(items),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "provider": self.provider,
            "goal": self.goal,
            "backend_mode": self.backend_mode,
            "items": [item.to_dict() for item in self.items],
            "count": self.count,
        }
