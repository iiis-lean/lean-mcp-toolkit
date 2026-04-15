"""Contracts for diagnostics.lint and sub-check outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..base import DictModel, JsonDict, to_bool, to_int, to_list_of_str
from .common import DiagnosticItem, Position


@dataclass(frozen=True)
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
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
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


@dataclass(frozen=True)
class CheckResult(DictModel):
    check_id: str
    success: bool
    message: str

    @classmethod
    def from_dict(cls, data: JsonDict) -> "CheckResult":
        return cls(
            check_id=str(data.get("check_id") or ""),
            success=bool(data.get("success", False)),
            message=str(data.get("message") or ""),
        )

    def to_dict(self) -> JsonDict:
        return {
            "check_id": self.check_id,
            "success": self.success,
            "message": self.message,
        }

    def to_markdown(self) -> str:
        return "\n".join(
            [
                f"- success: `{str(self.success).lower()}`",
                f"- message: {self.message}",
            ]
        )


@dataclass(frozen=True)
class AxiomDeclaredItem(DictModel):
    fileName: str | None
    declaration: str | None
    kind: str | None
    pos: Position | None = None
    endPos: Position | None = None
    content: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "AxiomDeclaredItem":
        return cls(
            fileName=(str(data["fileName"]) if data.get("fileName") is not None else None),
            declaration=(
                str(data["declaration"]) if data.get("declaration") is not None else None
            ),
            kind=(str(data["kind"]) if data.get("kind") is not None else None),
            pos=Position.from_dict(data["pos"]) if isinstance(data.get("pos"), dict) else None,
            endPos=(
                Position.from_dict(data["endPos"])
                if isinstance(data.get("endPos"), dict)
                else None
            ),
            content=(str(data["content"]) if data.get("content") is not None else None),
        )

    def to_dict(self) -> JsonDict:
        return {
            "fileName": self.fileName,
            "declaration": self.declaration,
            "kind": self.kind,
            "pos": self.pos.to_dict() if self.pos is not None else None,
            "endPos": self.endPos.to_dict() if self.endPos is not None else None,
            "content": self.content,
        }


@dataclass(frozen=True)
class AxiomUsageIssue(DictModel):
    fileName: str | None
    declaration: str | None
    risky_axioms: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "AxiomUsageIssue":
        risky = to_list_of_str(data.get("risky_axioms")) or []
        return cls(
            fileName=(str(data["fileName"]) if data.get("fileName") is not None else None),
            declaration=(str(data["declaration"]) if data.get("declaration") is not None else None),
            risky_axioms=tuple(risky),
        )

    def to_dict(self) -> JsonDict:
        return {
            "fileName": self.fileName,
            "declaration": self.declaration,
            "risky_axioms": list(self.risky_axioms),
        }


@dataclass(frozen=True)
class AxiomUsageUnresolved(DictModel):
    fileName: str | None
    declaration: str | None
    reason: str

    @classmethod
    def from_dict(cls, data: JsonDict) -> "AxiomUsageUnresolved":
        return cls(
            fileName=(str(data["fileName"]) if data.get("fileName") is not None else None),
            declaration=(str(data["declaration"]) if data.get("declaration") is not None else None),
            reason=str(data.get("reason") or ""),
        )

    def to_dict(self) -> JsonDict:
        return {
            "fileName": self.fileName,
            "declaration": self.declaration,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class AxiomAuditResult(CheckResult):
    check_id: Literal["axiom_audit"] = field(default="axiom_audit", init=False)
    declared_axioms: tuple[AxiomDeclaredItem, ...] = field(default_factory=tuple)
    usage_issues: tuple[AxiomUsageIssue, ...] = field(default_factory=tuple)
    unresolved: tuple[AxiomUsageUnresolved, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "AxiomAuditResult":
        raw_declared = data.get("declared_axioms")
        parsed_declared: list[AxiomDeclaredItem] = []
        if isinstance(raw_declared, list):
            for item in raw_declared:
                if isinstance(item, dict):
                    parsed_declared.append(AxiomDeclaredItem.from_dict(item))

        raw_issues = data.get("usage_issues")
        parsed_issues: list[AxiomUsageIssue] = []
        if isinstance(raw_issues, list):
            for item in raw_issues:
                if isinstance(item, dict):
                    parsed_issues.append(AxiomUsageIssue.from_dict(item))

        raw_unresolved = data.get("unresolved")
        parsed_unresolved: list[AxiomUsageUnresolved] = []
        if isinstance(raw_unresolved, list):
            for item in raw_unresolved:
                if isinstance(item, dict):
                    parsed_unresolved.append(AxiomUsageUnresolved.from_dict(item))

        return cls(
            success=bool(data.get("success", False)),
            message=str(data.get("message") or ""),
            declared_axioms=tuple(parsed_declared),
            usage_issues=tuple(parsed_issues),
            unresolved=tuple(parsed_unresolved),
        )

    def to_dict(self) -> JsonDict:
        return {
            "check_id": self.check_id,
            "success": self.success,
            "message": self.message,
            "declared_axioms": [item.to_dict() for item in self.declared_axioms],
            "usage_issues": [item.to_dict() for item in self.usage_issues],
            "unresolved": [item.to_dict() for item in self.unresolved],
        }

    def to_markdown(self) -> str:
        lines = [
            f"- success: `{str(self.success).lower()}`",
            f"- message: {self.message}",
            f"- declared_axioms: `{len(self.declared_axioms)}`",
            f"- usage_issues: `{len(self.usage_issues)}`",
            f"- unresolved: `{len(self.unresolved)}`",
        ]
        lines.append("")
        lines.append("##### Declared Axioms")
        if not self.declared_axioms:
            lines.append("- (empty)")
        else:
            for item in self.declared_axioms:
                location = _format_location(item.fileName, item.pos)
                declaration = (item.declaration or "").strip() or "<unknown>"
                kind = (item.kind or "").strip() or "unknown"
                if location:
                    lines.append(
                        f"error: {location}: declared axiom `{declaration}` (kind={kind})"
                    )
                else:
                    lines.append(f"error: declared axiom `{declaration}` (kind={kind})")
                if item.content:
                    lines.append("")
                    lines.append("```lean")
                    lines.append(item.content)
                    lines.append("```")

        lines.append("")
        lines.append("##### Axiom Usage Issues")
        if not self.usage_issues:
            lines.append("- (empty)")
        else:
            for item in self.usage_issues:
                location = _display_file_name(item.fileName)
                declaration = (item.declaration or "").strip() or "<unknown>"
                risky_text = ", ".join(ax for ax in item.risky_axioms if ax.strip()) or "(none)"
                if location:
                    lines.append(
                        f"error: {location}: declaration `{declaration}` uses risky axioms: {risky_text}"
                    )
                else:
                    lines.append(
                        f"error: declaration `{declaration}` uses risky axioms: {risky_text}"
                    )

        lines.append("")
        lines.append("##### Unresolved Declarations")
        if not self.unresolved:
            lines.append("- (empty)")
        else:
            for item in self.unresolved:
                location = _display_file_name(item.fileName)
                declaration = (item.declaration or "").strip()
                reason = (item.reason or "").strip() or "unknown reason"
                if declaration:
                    if location:
                        lines.append(
                            f"error: {location}: declaration `{declaration}` unresolved: {reason}"
                        )
                    else:
                        lines.append(f"error: declaration `{declaration}` unresolved: {reason}")
                else:
                    if location:
                        lines.append(
                            f"error: {location}: unresolved declaration audit: {reason}"
                        )
                    else:
                        lines.append(f"error: unresolved declaration audit: {reason}")
        return "\n".join(lines)


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


def _format_location(file_name: str | None, pos: Position | None) -> str | None:
    location = _display_file_name(file_name)
    if pos is not None:
        if location:
            return f"{location}:{pos.line}:{pos.column}"
        return f"{pos.line}:{pos.column}"
    return location


@dataclass(frozen=True)
class NoSorryResult(CheckResult):
    check_id: Literal["no_sorry"] = field(default="no_sorry", init=False)
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
            f"- success: `{str(self.success).lower()}`",
            f"- message: {self.message}",
            f"- sorries: `{len(self.sorries)}`",
        ]
        if self.sorries:
            lines.append("")
            lines.extend(item.to_markdown() for item in self.sorries)
        return "\n".join(lines)


LintCheckResult = CheckResult | NoSorryResult | AxiomAuditResult


@dataclass(frozen=True)
class LintResponse(DictModel):
    success: bool
    checks: tuple[LintCheckResult, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "LintResponse":
        parsed: list[LintCheckResult] = []
        raw = data.get("checks")
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                check_id = str(item.get("check_id") or "")
                if check_id == "no_sorry":
                    parsed.append(NoSorryResult.from_dict(item))
                elif check_id == "axiom_audit":
                    parsed.append(AxiomAuditResult.from_dict(item))
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
        for check in self.checks:
            check_id = getattr(check, "check_id", "").strip() or "unknown_check"
            chunks.append(f"{'#' * max(1, title_level + 1)} `{check_id}`")
            chunks.append(check.to_markdown())
        return "\n\n".join(chunks)
