"""Contracts for build.workspace."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..base import DictModel, JsonDict, to_bool, to_int, to_list_of_str


@dataclass(slots=True, frozen=True)
class BuildWorkspaceRequest(DictModel):
    project_root: str | None = None
    targets: tuple[str, ...] | None = None
    target_facet: str | None = None
    jobs: int | None = None
    timeout_seconds: int | None = None
    clean_first: bool | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "BuildWorkspaceRequest":
        targets = to_list_of_str(data.get("targets"))
        return cls(
            project_root=(
                str(data["project_root"]) if data.get("project_root") is not None else None
            ),
            targets=(tuple(targets) if targets is not None else None),
            target_facet=(
                str(data["target_facet"]).strip()
                if data.get("target_facet") is not None and str(data["target_facet"]).strip()
                else None
            ),
            jobs=to_int(data.get("jobs"), default=None) if "jobs" in data else None,
            timeout_seconds=(
                to_int(data.get("timeout_seconds"), default=None)
                if "timeout_seconds" in data
                else None
            ),
            clean_first=(
                to_bool(data.get("clean_first"), default=False)
                if "clean_first" in data
                else None
            ),
        )

    def to_dict(self) -> JsonDict:
        return {
            "project_root": self.project_root,
            "targets": list(self.targets) if self.targets is not None else None,
            "target_facet": self.target_facet,
            "jobs": self.jobs,
            "timeout_seconds": self.timeout_seconds,
            "clean_first": self.clean_first,
        }


@dataclass(slots=True, frozen=True)
class BuildWorkspaceResponse(DictModel):
    success: bool
    error_message: str | None = None
    project_root: str = ""
    targets: tuple[str, ...] = field(default_factory=tuple)
    target_facet: str | None = None
    jobs: int | None = None
    executed_commands: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
    returncode: int = 0
    timed_out: bool = False
    stdout: str = ""
    stderr: str = ""

    @classmethod
    def from_dict(cls, data: JsonDict) -> "BuildWorkspaceResponse":
        raw_commands = data.get("executed_commands")
        commands: list[tuple[str, ...]] = []
        if isinstance(raw_commands, list):
            for item in raw_commands:
                if isinstance(item, list):
                    commands.append(tuple(str(part) for part in item))
        raw_targets = data.get("targets")
        targets = tuple(str(item) for item in raw_targets) if isinstance(raw_targets, list) else tuple()
        return cls(
            success=bool(data.get("success", False)),
            error_message=(
                str(data["error_message"]) if data.get("error_message") is not None else None
            ),
            project_root=str(data.get("project_root") or ""),
            targets=targets,
            target_facet=(
                str(data["target_facet"]) if data.get("target_facet") is not None else None
            ),
            jobs=to_int(data.get("jobs"), default=None),
            executed_commands=tuple(commands),
            returncode=int(data.get("returncode") or 0),
            timed_out=bool(data.get("timed_out", False)),
            stdout=str(data.get("stdout") or ""),
            stderr=str(data.get("stderr") or ""),
        )

    def to_dict(self) -> JsonDict:
        return {
            "success": self.success,
            "error_message": self.error_message,
            "project_root": self.project_root,
            "targets": list(self.targets),
            "target_facet": self.target_facet,
            "jobs": self.jobs,
            "executed_commands": [list(item) for item in self.executed_commands],
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }

    def to_markdown(
        self,
        *,
        title: str | None = "Workspace Build",
        title_level: int = 2,
    ) -> str:
        chunks: list[str] = []
        if title:
            chunks.append(f"{'#' * max(1, title_level)} {title}")
        chunks.append(f"- success: `{str(self.success).lower()}`")
        chunks.append(f"- project_root: `{self.project_root}`")
        chunks.append(f"- targets: `{list(self.targets)}`")
        chunks.append(f"- target_facet: `{self.target_facet or 'none'}`")
        chunks.append(f"- jobs: `{self.jobs if self.jobs is not None else 'default'}`")
        chunks.append(f"- returncode: `{self.returncode}`")
        chunks.append(f"- timed_out: `{str(self.timed_out).lower()}`")
        if self.error_message:
            chunks.append(f"- error_message: {self.error_message}")
        if self.executed_commands:
            chunks.append("- executed_commands:")
            for command in self.executed_commands:
                chunks.append(f"  - `{ ' '.join(command) }`")
        if self.stdout.strip():
            chunks.append("")
            chunks.append("```text")
            chunks.append(self.stdout.rstrip())
            chunks.append("```")
        if self.stderr.strip():
            chunks.append("")
            chunks.append("```text")
            chunks.append(self.stderr.rstrip())
            chunks.append("```")
        return "\n".join(chunks)
