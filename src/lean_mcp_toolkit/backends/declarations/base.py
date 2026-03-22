"""Backend interface for declaration extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from lean_interact.interface import DeclarationInfo as LeanDeclarationInfo
    from lean_interact.interface import Message as LeanMessage
    from lean_interact.interface import Sorry as LeanSorry
else:  # pragma: no cover - runtime typing fallback when lean_interact is absent
    LeanDeclarationInfo = Any
    LeanMessage = Any
    LeanSorry = Any


@dataclass(slots=True, frozen=True)
class DeclarationsBackendRequest:
    project_root: Path
    target_dot: str
    timeout_seconds: int | None = None


@dataclass(slots=True, frozen=True)
class DeclarationsBackendResponse:
    success: bool
    error_message: str | None = None
    declarations: tuple[LeanDeclarationInfo, ...] = field(default_factory=tuple)
    messages: tuple[LeanMessage, ...] = field(default_factory=tuple)
    sorries: tuple[LeanSorry, ...] = field(default_factory=tuple)


class DeclarationsBackend(Protocol):
    backend_name: str

    def extract(self, req: DeclarationsBackendRequest) -> DeclarationsBackendResponse:
        ...
