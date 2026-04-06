"""Startup warmup runner for selected toolkit backends/tools."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from pathlib import Path
from typing import Any
import uuid

from ..config import ToolkitConfig
from ..contracts.base import JsonDict
from ..contracts.declarations import DeclarationExtractRequest
from ..contracts.diagnostics import FileRequest
from ..contracts.search_core import MathlibDeclFindRequest
from ..core.services import DeclarationsService, DiagnosticsService, SearchCoreService

_PROBE_MARKER = "lean-mcp-toolkit:warmup-probe"
_DEFAULT_PROBE_CONTENT = (
    f"/- {_PROBE_MARKER} -/\n"
    "namespace LeanMcpToolkitWarmup\n\n"
    "def probeNat : Nat := 1\n\n"
    "theorem probeEq : probeNat = 1 := by\n"
    "  rfl\n\n"
    "end LeanMcpToolkitWarmup\n"
)


@dataclass(slots=True, frozen=True)
class WarmupStepReport:
    call_name: str
    success: bool
    skipped: bool = False
    elapsed_ms: int | None = None
    error_message: str | None = None

    def to_dict(self) -> JsonDict:
        return {
            "call_name": self.call_name,
            "success": self.success,
            "skipped": self.skipped,
            "elapsed_ms": self.elapsed_ms,
            "error_message": self.error_message,
        }


@dataclass(slots=True, frozen=True)
class WarmupReport:
    enabled: bool
    executed: bool
    success: bool
    project_root: str | None
    steps: tuple[WarmupStepReport, ...] = field(default_factory=tuple)

    def to_dict(self) -> JsonDict:
        return {
            "enabled": self.enabled,
            "executed": self.executed,
            "success": self.success,
            "project_root": self.project_root,
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(slots=True, frozen=True)
class _ProbeHandle:
    abs_path: Path
    rel_path: str


@dataclass(slots=True)
class ToolkitWarmupRunner:
    config: ToolkitConfig
    diagnostics: DiagnosticsService | None
    declarations: DeclarationsService | None
    search_core: SearchCoreService | None

    def run(self) -> WarmupReport:
        policy = self.config.warmup.policy
        if not policy.enabled:
            return WarmupReport(
                enabled=False,
                executed=False,
                success=True,
                project_root=None,
                steps=tuple(),
            )

        default_root, root_error = self._resolve_default_project_root()
        steps: list[WarmupStepReport] = []
        probe_handle: _ProbeHandle | None = None
        probe_error: str | None = None

        try:
            for call_name in self.config.warmup.plan.order:
                call_cfg = self.config.warmup.calls.get(call_name)
                if call_cfg is None:
                    steps.append(
                        WarmupStepReport(
                            call_name=call_name,
                            success=False,
                            skipped=False,
                            elapsed_ms=0,
                            error_message=f"unknown warmup call: {call_name}",
                        )
                    )
                    continue

                if not call_cfg.enabled:
                    steps.append(
                        WarmupStepReport(
                            call_name=call_name,
                            success=True,
                            skipped=True,
                            elapsed_ms=0,
                            error_message=None,
                        )
                    )
                    continue

                if call_cfg.use_probe_file and probe_handle is None and probe_error is None:
                    if root_error is not None:
                        probe_error = root_error
                    elif default_root is None:
                        probe_error = (
                            "warmup probe requires project_root, but no default_project_root is configured"
                        )
                    else:
                        try:
                            probe_handle = self._prepare_probe_file(default_root)
                        except Exception as exc:
                            probe_error = str(exc)

                started = time.perf_counter()
                try:
                    if call_cfg.use_probe_file and probe_error is not None:
                        raise RuntimeError(probe_error)
                    self._run_single_call(
                        call_name=call_name,
                        default_root=default_root,
                        call_request=call_cfg.request,
                        use_probe_file=call_cfg.use_probe_file,
                        probe_handle=probe_handle,
                    )
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    steps.append(
                        WarmupStepReport(
                            call_name=call_name,
                            success=True,
                            elapsed_ms=elapsed_ms,
                        )
                    )
                except Exception as exc:
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    steps.append(
                        WarmupStepReport(
                            call_name=call_name,
                            success=False,
                            elapsed_ms=elapsed_ms,
                            error_message=str(exc),
                        )
                    )
        finally:
            if probe_handle is not None and self.config.warmup.probe_file.cleanup:
                try:
                    probe_handle.abs_path.unlink(missing_ok=True)
                except Exception:
                    pass
                try:
                    parent = probe_handle.abs_path.parent
                    if parent.exists() and parent.is_dir() and not any(parent.iterdir()):
                        parent.rmdir()
                except Exception:
                    pass

        success = all(step.success for step in steps)
        return WarmupReport(
            enabled=True,
            executed=True,
            success=success,
            project_root=(str(default_root) if default_root is not None else None),
            steps=tuple(steps),
        )

    def _resolve_default_project_root(self) -> tuple[Path | None, str | None]:
        raw = (
            self.config.warmup.policy.default_project_root
            or self.config.server.default_project_root
        )
        if raw is None or not str(raw).strip():
            return None, None
        path = Path(raw).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            return None, f"default_project_root is not a directory: {path}"
        return path, None

    def _prepare_probe_file(self, project_root: Path) -> _ProbeHandle:
        rel_path = self.config.warmup.probe_file.rel_path.strip().replace("\\", "/")
        if not rel_path:
            raise ValueError("warmup.probe_file.rel_path must not be empty")

        base = (project_root / rel_path).resolve()
        try:
            base.relative_to(project_root)
        except Exception as exc:
            raise ValueError(
                f"warmup probe rel_path resolves outside project_root: {rel_path}"
            ) from exc

        target = base
        if target.exists() and self.config.warmup.probe_file.conflict_strategy == "suffix_if_exists":
            suffix = target.suffix or ".lean"
            stem = target.stem or "Probe"
            target = target.with_name(f"{stem}_{uuid.uuid4().hex[:8]}{suffix}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_DEFAULT_PROBE_CONTENT, encoding="utf-8")
        rel = target.relative_to(project_root).as_posix()
        return _ProbeHandle(abs_path=target, rel_path=rel)

    def _run_single_call(
        self,
        *,
        call_name: str,
        default_root: Path | None,
        call_request: JsonDict,
        use_probe_file: bool,
        probe_handle: _ProbeHandle | None,
    ) -> None:
        if call_name == "lean_explore.find":
            if self.search_core is None:
                raise RuntimeError("search_core service is not available")
            req = MathlibDeclFindRequest.from_dict(dict(call_request))
            self.search_core.run_mathlib_decl_find(req)
            return

        if call_name == "declarations.extract":
            if self.declarations is None:
                raise RuntimeError("declarations service is not available")
            payload = dict(call_request)
            if use_probe_file:
                if probe_handle is None or default_root is None:
                    raise RuntimeError("warmup probe is not prepared")
                payload["target"] = probe_handle.rel_path
                payload["project_root"] = str(default_root)
            else:
                if default_root is not None and payload.get("project_root") is None:
                    payload["project_root"] = str(default_root)
            req = DeclarationExtractRequest.from_dict(payload)
            resp = self.declarations.extract(req)
            if not resp.success:
                raise RuntimeError(resp.error_message or "declarations.extract warmup failed")
            return

        if call_name == "diagnostics.file":
            if self.diagnostics is None:
                raise RuntimeError("diagnostics service is not available")
            payload = dict(call_request)
            if use_probe_file:
                if probe_handle is None or default_root is None:
                    raise RuntimeError("warmup probe is not prepared")
                payload["file_path"] = probe_handle.rel_path
                payload["project_root"] = str(default_root)
            else:
                if default_root is not None and payload.get("project_root") is None:
                    payload["project_root"] = str(default_root)
            req = FileRequest.from_dict(payload)
            resp = self.diagnostics.run_file(req)
            if not resp.success:
                raise RuntimeError(resp.error_message or "diagnostics.file warmup failed")
            return

        raise RuntimeError(f"unsupported warmup call: {call_name}")


__all__ = [
    "ToolkitWarmupRunner",
    "WarmupReport",
    "WarmupStepReport",
]
