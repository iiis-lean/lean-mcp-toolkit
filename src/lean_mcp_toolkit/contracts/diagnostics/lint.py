"""Contracts for diagnostics.lint and sub-check outputs."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool, to_int, to_list_of_str
from .common import DiagnosticItem


@dataclass(slots=True, frozen=True)
class LintRequest(DictModel):
    project_root: str | None = None
    targets: tuple[str, ...] | None = None
    enabled_checks: tuple[str, ...] | None = None
    include_content: bool | None = None
    context_lines: int | None = None
    timeout_seconds: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LintRequest":
        targets = to_list_of_str(data.get("targets"))
        enabled_checks = to_list_of_str(data.get("enabled_checks"))
        include_content = (
            to_bool(data.get("include_content"), default=True)
            if "include_content" in data
            else None
        )
        context_lines = (
            to_int(data.get("context_lines"), default=2)
            if "context_lines" in data
            else None
        )
        return cls(
            project_root=(str(data["project_root"]) if data.get("project_root") is not None else None),
            targets=(tuple(targets) if targets is not None else None),
            enabled_checks=(tuple(enabled_checks) if enabled_checks is not None else None),
            include_content=include_content,
            context_lines=context_lines,
            timeout_seconds=(
                to_int(data.get("timeout_seconds"), default=None)
                if "timeout_seconds" in data
                else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "targets": list(self.targets) if self.targets is not None else None,
            "enabled_checks": list(self.enabled_checks) if self.enabled_checks is not None else None,
            "include_content": self.include_content,
            "context_lines": self.context_lines,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(slots=True, frozen=True)
class CheckResult(DictModel):
    check_id: str
    success: bool
    message: str
    fields: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "CheckResult":
        known = {"check_id", "success", "message"}
        rest: JsonDict = {
            k: v
            for k, v in data.items()
            if k not in known
        }
        return cls(
            check_id=str(data.get("check_id") or ""),
            success=bool(data.get("success", False)),
            message=str(data.get("message") or ""),
            fields=rest,
        )

    def to_dict(self) -> JsonDict:
        merged: JsonDict = {
            "check_id": self.check_id,
            "success": self.success,
            "message": self.message,
        }
        merged.update(self.fields)
        return merged

    def to_markdown(self) -> str:
        lines = [
            f"- check_id: `{self.check_id}`",
            f"- success: `{str(self.success).lower()}`",
            f"- message: {self.message}",
        ]
        if self.fields:
            lines.append("- extra_fields:")
            for key, value in self.fields.items():
                lines.append(f"  - {key}: `{value}`")
        return "\n".join(lines)


@dataclass(slots=True, frozen=True)
class NoSorryResult(DictModel):
    check_id: str
    success: bool
    message: str
    sorries: tuple[DiagnosticItem, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "NoSorryResult":
        raw = data.get("sorries")
        sorries: list[DiagnosticItem] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    sorries.append(DiagnosticItem.from_dict(item))
        return cls(
            check_id=str(data.get("check_id") or "no_sorry"),
            success=bool(data.get("success", False)),
            message=str(data.get("message") or ""),
            sorries=tuple(sorries),
        )

    def to_dict(self) -> JsonDict:
        return {
            "check_id": self.check_id,
            "success": self.success,
            "message": self.message,
            "sorries": [item.to_dict() for item in self.sorries],
        }

    def to_markdown(self) -> str:
        lines = [
            f"- check_id: `{self.check_id}`",
            f"- success: `{str(self.success).lower()}`",
            f"- message: {self.message}",
            f"- sorries: `{len(self.sorries)}`",
        ]
        if self.sorries:
            lines.append("")
            lines.extend(item.to_markdown() for item in self.sorries)
        return "\n".join(lines)


@dataclass(slots=True, frozen=True)
class LintResponse(DictModel):
    success: bool
    checks: tuple[CheckResult | NoSorryResult, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LintResponse":
        parsed: list[CheckResult | NoSorryResult] = []
        raw = data.get("checks")
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                check_id = str(item.get("check_id") or "")
                if check_id == "no_sorry":
                    parsed.append(NoSorryResult.from_dict(item))
                else:
                    parsed.append(CheckResult.from_dict(item))
        return cls(success=bool(data.get("success", False)), checks=tuple(parsed))

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "checks": [c.to_dict() for c in self.checks],
        }

    def to_markdown(self, *, title: str | None = "Lint Results", title_level: int = 2) -> str:
        chunks: list[str] = []
        if title:
            chunks.append(f"{'#' * max(1, title_level)} {title}")
        chunks.append(f"- success: `{str(self.success).lower()}`")
        chunks.append(f"- checks: `{len(self.checks)}`")
        for idx, check in enumerate(self.checks, start=1):
            chunks.append(f"{'#' * max(1, title_level + 1)} Check {idx}")
            chunks.append(check.to_markdown())
        return "\n\n".join(chunks)
