"""LeanInteract backend for declarations extraction."""

from __future__ import annotations

from typing import Any

from ...config import LeanInteractBackendConfig, ToolchainConfig
from ..lean_interact_runtime import LeanInteractRuntimeManager
from ..lean.path import LeanPath
from .base import DeclarationsBackendRequest, DeclarationsBackendResponse


class LeanInteractDeclarationsBackend:
    """Declarations backend implemented on top of LeanInteract."""

    backend_name = "lean_interact"

    def __init__(
        self,
        *,
        toolchain_config: ToolchainConfig,
        backend_config: LeanInteractBackendConfig,
        runtime_manager: LeanInteractRuntimeManager | None = None,
    ):
        self.toolchain_config = toolchain_config
        self.backend_config = backend_config
        self.runtime_manager = runtime_manager or LeanInteractRuntimeManager(
            toolchain_config=toolchain_config,
            backend_config=backend_config,
        )

    def close(self) -> None:
        self.runtime_manager.close()

    def extract(self, req: DeclarationsBackendRequest) -> DeclarationsBackendResponse:
        rel_file = LeanPath.from_dot(req.target_dot).to_rel_file()
        return self._extract_rel_file(req=req, rel_file=rel_file)

    def extract_batch(
        self,
        reqs: tuple[DeclarationsBackendRequest, ...],
    ) -> tuple[DeclarationsBackendResponse, ...]:
        if not reqs:
            return tuple()
        requests = tuple(
            self.runtime_manager.make_file_command(
                rel_file=LeanPath.from_dot(req.target_dot).to_rel_file(),
                declarations=True,
            )
            for req in reqs
        )
        try:
            project_root = reqs[0].project_root
            timeout = float(reqs[0].timeout_seconds) if reqs[0].timeout_seconds is not None else None
            responses = self.runtime_manager.run_batch(
                project_root=project_root,
                requests=requests,
                timeout_per_req=timeout,
            )
        except Exception as exc:
            if self._should_recycle_runtime(exc):
                self.runtime_manager.recycle_runtime(project_root)
            error = f"lean_interact execution failed: {self._format_exception(exc)}"
            return tuple(
                DeclarationsBackendResponse(
                    success=False,
                    error_message=error,
                    declarations=tuple(),
                    messages=tuple(),
                    sorries=tuple(),
                )
                for _ in reqs
            )
        return tuple(self._build_response(response) for response in responses)

    def _extract_rel_file(
        self,
        *,
        req: DeclarationsBackendRequest,
        rel_file: str,
    ) -> DeclarationsBackendResponse:
        try:
            file_command = self.runtime_manager.make_file_command(
                rel_file=rel_file,
                declarations=True,
            )
            timeout = float(req.timeout_seconds) if req.timeout_seconds is not None else None
            response = self.runtime_manager.run(
                project_root=req.project_root,
                request=file_command,
                timeout=timeout,
            )
        except Exception as exc:
            if self._should_recycle_runtime(exc):
                self.runtime_manager.recycle_runtime(req.project_root)
            return DeclarationsBackendResponse(
                success=False,
                error_message=f"lean_interact execution failed: {self._format_exception(exc)}",
                declarations=tuple(),
                messages=tuple(),
                sorries=tuple(),
            )
        return self._build_response(response)

    def _build_response(self, response: Any) -> DeclarationsBackendResponse:
        if self._is_lean_error(response):
            return DeclarationsBackendResponse(
                success=False,
                error_message=self._lean_error_message(response),
                declarations=tuple(),
                messages=tuple(),
                sorries=tuple(),
            )

        declarations = self._collect_sequence(getattr(response, "declarations", None))
        messages = self._collect_sequence(getattr(response, "messages", None))
        sorries = self._collect_sequence(getattr(response, "sorries", None))

        if self._response_has_errors(response):
            return DeclarationsBackendResponse(
                success=False,
                error_message=self._format_response_errors(response),
                declarations=declarations,
                messages=messages,
                sorries=sorries,
            )

        return DeclarationsBackendResponse(
            success=True,
            error_message=None,
            declarations=declarations,
            messages=messages,
            sorries=sorries,
        )

    def _is_lean_error(self, response: Any) -> bool:
        lean_error_cls = self.runtime_manager.lean_error_cls()
        return isinstance(response, lean_error_cls)

    @staticmethod
    def _lean_error_message(response: Any) -> str:
        message = getattr(response, "message", None)
        return str(message or "unknown LeanInteract error")

    @staticmethod
    def _response_has_errors(response: Any) -> bool:
        has_errors = getattr(response, "has_errors", None)
        if callable(has_errors):
            return bool(has_errors())
        return False

    @staticmethod
    def _format_response_errors(response: Any) -> str:
        messages = getattr(response, "messages", None)
        if not isinstance(messages, list) or not messages:
            return "LeanInteract response contains errors"
        errors = []
        for msg in messages:
            severity = getattr(msg, "severity", None)
            if severity != "error":
                continue
            data = getattr(msg, "data", None)
            if data:
                errors.append(str(data))
        if not errors:
            return "LeanInteract response contains errors"
        return "; ".join(errors[:3])

    @staticmethod
    def _collect_sequence(value: Any) -> tuple[Any, ...]:
        if isinstance(value, list):
            return tuple(value)
        if isinstance(value, tuple):
            return value
        return tuple()

    @staticmethod
    def _format_exception(exc: Exception) -> str:
        message = str(exc).strip()
        if message:
            return message
        return exc.__class__.__name__

    @staticmethod
    def _should_recycle_runtime(exc: Exception) -> bool:
        if isinstance(exc, TimeoutError):
            return True
        lowered = str(exc).strip().lower()
        return "timed out" in lowered or "timeout" in lowered or "deadline" in lowered
