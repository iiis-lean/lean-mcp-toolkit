"""Contracts for diagnostics.build."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..base import DictModel, JsonDict, to_bool, to_int, to_list_of_str
from .common import FileDiagnostics

BuildFailedStage = Literal["build_deps", "diagnostics", "emit_artifacts"] | None


@dataclass(slots=True, frozen=True)
class BuildRequest(DictModel):
    project_root: str | None = None
    targets: tuple[str, ...] | None = None
    build_deps: bool | None = None
    emit_artifacts: bool | None = None
    include_content: bool | None = None
    context_lines: int | None = None
    timeout_seconds: int | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "BuildRequest":
        targets = to_list_of_str(data.get("targets"))
        build_deps = (
            to_bool(data.get("build_deps"), default=False) if "build_deps" in data else None
        )
        emit_artifacts = (
            to_bool(data.get("emit_artifacts"), default=False)
            if "emit_artifacts" in data
            else None
        )
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
            build_deps=build_deps,
            emit_artifacts=emit_artifacts,
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
            "build_deps": self.build_deps,
            "emit_artifacts": self.emit_artifacts,
            "include_content": self.include_content,
            "context_lines": self.context_lines,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(slots=True, frozen=True)
class BuildResponse(DictModel):
    success: bool
    files: tuple[FileDiagnostics, ...] = field(default_factory=tuple)
    failed_stage: BuildFailedStage = None
    stage_error_message: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "BuildResponse":
        raw_files = data.get("files")
        parsed_files: list[FileDiagnostics] = []
        if isinstance(raw_files, list):
            for file_item in raw_files:
                if isinstance(file_item, dict):
                    parsed_files.append(FileDiagnostics.from_dict(file_item))
        raw_failed_stage = data.get("failed_stage")
        failed_stage: BuildFailedStage = None
        if raw_failed_stage in {"build_deps", "diagnostics", "emit_artifacts"}:
            failed_stage = raw_failed_stage  # type: ignore[assignment]
        return cls(
            success=bool(data.get("success", False)),
            files=tuple(parsed_files),
            failed_stage=failed_stage,
            stage_error_message=(
                str(data["stage_error_message"])
                if data.get("stage_error_message") is not None
                else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "files": [f.to_dict() for f in self.files],
            "failed_stage": self.failed_stage,
            "stage_error_message": self.stage_error_message,
        }

    def to_markdown(self, *, title: str | None = "Build Diagnostics", title_level: int = 2) -> str:
        chunks: list[str] = []
        if title:
            chunks.append(f"{'#' * max(1, title_level)} {title}")
        chunks.append(f"- success: `{str(self.success).lower()}`")
        chunks.append(f"- failed_stage: `{self.failed_stage or 'none'}`")
        if self.stage_error_message:
            chunks.append(f"- stage_error_message: {self.stage_error_message}")
        if not self.files:
            chunks.append("- files: (empty)")
            return "\n\n".join(chunks)

        chunks.append(f"- files: `{len(self.files)}`")
        for file_result in self.files:
            chunks.append(file_result.to_markdown(title_level=title_level + 1))
        return "\n\n".join(chunks)
