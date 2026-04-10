"""Per-call audit logging and stage timing helpers for toolkit services."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import json
from pathlib import Path
import threading
import time
import uuid
from typing import Any, Iterator

from .config import ToolkitAuditConfig, ToolkitConfig

_CURRENT_AUDIT_RECORDER: ContextVar["CallTimingRecorder | None"] = ContextVar(
    "toolkit_current_audit_recorder",
    default=None,
)
_CURRENT_TOOL_VIEW: ContextVar[str] = ContextVar(
    "toolkit_current_tool_view",
    default="default",
)


def _utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _jsonify(value: Any) -> Any:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _jsonify(value.to_dict())
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    return str(value)


@dataclass(slots=True, frozen=True)
class CallStageTiming:
    name: str
    status: str
    started_at: str
    finished_at: str
    elapsed_seconds: float
    attrs: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_seconds": self.elapsed_seconds,
            "attrs": _jsonify(self.attrs),
            "error_message": self.error_message,
        }


@dataclass(slots=True)
class CallTimingRecorder:
    call_id: str
    tool_name: str
    started_at: str = field(default_factory=_utc_now_iso)
    attrs: dict[str, Any] = field(default_factory=dict)
    _start_monotonic: float = field(default_factory=time.perf_counter, init=False, repr=False)
    _stages: list[CallStageTiming] = field(default_factory=list, init=False, repr=False)

    @contextmanager
    def stage(self, name: str, *, attrs: dict[str, Any] | None = None) -> Iterator[None]:
        started_at = _utc_now_iso()
        started = time.perf_counter()
        try:
            yield
        except Exception as exc:
            self._stages.append(
                CallStageTiming(
                    name=name,
                    status="failed",
                    started_at=started_at,
                    finished_at=_utc_now_iso(),
                    elapsed_seconds=time.perf_counter() - started,
                    attrs=dict(attrs or {}),
                    error_message=str(exc),
                )
            )
            raise
        else:
            self._stages.append(
                CallStageTiming(
                    name=name,
                    status="completed",
                    started_at=started_at,
                    finished_at=_utc_now_iso(),
                    elapsed_seconds=time.perf_counter() - started,
                    attrs=dict(attrs or {}),
                )
            )

    def set_attr(self, key: str, value: Any) -> None:
        self.attrs[key] = _jsonify(value)

    def snapshot(self, *, status: str, error_message: str | None = None) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "started_at": self.started_at,
            "finished_at": _utc_now_iso(),
            "total_elapsed_seconds": time.perf_counter() - self._start_monotonic,
            "status": status,
            "error_message": error_message,
            "attrs": _jsonify(self.attrs),
            "stages": [item.to_dict() for item in self._stages],
        }


def get_current_audit_recorder() -> CallTimingRecorder | None:
    return _CURRENT_AUDIT_RECORDER.get()


def get_current_tool_view() -> str:
    return _normalize_view_name(_CURRENT_TOOL_VIEW.get())


@contextmanager
def audit_view(view_name: str | None) -> Iterator[None]:
    token = _CURRENT_TOOL_VIEW.set(_normalize_view_name(view_name))
    try:
        yield
    finally:
        _CURRENT_TOOL_VIEW.reset(token)


@contextmanager
def audit_stage(name: str, *, attrs: dict[str, Any] | None = None) -> Iterator[None]:
    recorder = get_current_audit_recorder()
    if recorder is None:
        yield
        return
    with recorder.stage(name, attrs=attrs):
        yield


class ToolkitAuditLogger:
    def __init__(self, config: ToolkitConfig):
        self.config = config
        self.audit_config: ToolkitAuditConfig = config.audit
        self._jsonl_lock = threading.Lock()

    def enabled(self) -> bool:
        return bool(self.audit_config.enabled)

    def new_call_id(self) -> str:
        return f"tk_{uuid.uuid4().hex}"

    @contextmanager
    def bind_recorder(self, recorder: CallTimingRecorder) -> Iterator[None]:
        token = _CURRENT_AUDIT_RECORDER.set(recorder)
        try:
            yield
        finally:
            _CURRENT_AUDIT_RECORDER.reset(token)

    def resolve_root(self, project_root: str | None) -> Path:
        if project_root:
            return Path(project_root).expanduser().resolve() / ".runtime" / "toolkit"
        global_root = (self.audit_config.global_root or "").strip()
        if global_root:
            return Path(global_root).expanduser().resolve()
        return Path.home() / ".cache" / "lean_mcp_toolkit" / "audit"

    def save_call(
        self,
        *,
        call_id: str,
        tool_name: str,
        group_name: str,
        method_name: str,
        project_root: str | None,
        request_payload: Any,
        response_payload: Any,
        timing_payload: dict[str, Any],
        status: str,
        error_message: str | None,
    ) -> None:
        if not self.enabled():
            return
        root = self.resolve_root(project_root)
        view_name = get_current_tool_view()
        view_root = root / "views" / view_name
        call_dir = view_root / "calls" / call_id
        call_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "call_id": call_id,
            "tool_name": tool_name,
            "group_name": group_name,
            "method_name": method_name,
            "project_root": project_root,
            "view": view_name,
            "status": status,
            "error_message": error_message,
            "started_at": timing_payload.get("started_at"),
            "finished_at": timing_payload.get("finished_at"),
            "total_elapsed_seconds": timing_payload.get("total_elapsed_seconds"),
        }
        (call_dir / "meta.json").write_text(
            json.dumps(_jsonify(meta), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (call_dir / "timing.json").write_text(
            json.dumps(_jsonify(timing_payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if self.audit_config.save_request_payload:
            (call_dir / "request.json").write_text(
                json.dumps(_jsonify(request_payload), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if self.audit_config.save_response_payload:
            (call_dir / "response.json").write_text(
                json.dumps(_jsonify(response_payload), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        summary = dict(meta)
        with self._jsonl_lock:
            root.mkdir(parents=True, exist_ok=True)
            with (root / "calls.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(_jsonify(summary), ensure_ascii=False) + "\n")
            view_root.mkdir(parents=True, exist_ok=True)
            with (view_root / "calls.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(_jsonify(summary), ensure_ascii=False) + "\n")

    def load_call_meta(
        self,
        *,
        project_root: str | None,
        call_id: str,
        view: str | None = None,
    ) -> dict[str, Any] | None:
        path = self._call_file_path(project_root=project_root, call_id=call_id, view=view, filename="meta.json")
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_call_timing(
        self,
        *,
        project_root: str | None,
        call_id: str,
        view: str | None = None,
    ) -> dict[str, Any] | None:
        path = self._call_file_path(project_root=project_root, call_id=call_id, view=view, filename="timing.json")
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def tail_calls(
        self,
        *,
        project_root: str | None,
        view: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        root = self.resolve_root(project_root)
        path = (
            root / "views" / _normalize_view_name(view) / "calls.jsonl"
            if view
            else root / "calls.jsonl"
        )
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        rows: list[dict[str, Any]] = []
        for line in lines[-max(limit, 1) :]:
            try:
                decoded = json.loads(line)
            except Exception:
                continue
            if isinstance(decoded, dict):
                rows.append(decoded)
        return rows

    def _call_file_path(
        self,
        *,
        project_root: str | None,
        call_id: str,
        view: str | None,
        filename: str,
    ) -> Path:
        root = self.resolve_root(project_root)
        view_name = _normalize_view_name(view) if view else self._find_call_view(root, call_id)
        if view_name:
            path = root / "views" / view_name / "calls" / call_id / filename
            if path.exists():
                return path
        return root / "calls" / call_id / filename

    def _find_call_view(self, root: Path, call_id: str) -> str | None:
        path = root / "calls.jsonl"
        if not path.exists():
            return None
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            try:
                decoded = json.loads(line)
            except Exception:
                continue
            if isinstance(decoded, dict) and decoded.get("call_id") == call_id:
                view = decoded.get("view")
                return _normalize_view_name(str(view)) if view else "default"
        return None


class AuditedServiceProxy:
    def __init__(
        self,
        *,
        service: Any,
        group_name: str,
        logger: ToolkitAuditLogger,
        method_aliases: dict[str, str] | None = None,
    ):
        self._service = service
        self._group_name = group_name
        self._logger = logger
        self._method_aliases = dict(method_aliases or {})

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._service, name)
        if name == "close":
            return target
        if not callable(target) or name.startswith("_"):
            return target

        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            tool_name = self._method_aliases.get(name, f"{self._group_name}.{name}")
            project_root = _extract_project_root(args, kwargs, service=self._service)
            call_id = self._logger.new_call_id()
            recorder = CallTimingRecorder(call_id=call_id, tool_name=tool_name)
            recorder.set_attr("group_name", self._group_name)
            recorder.set_attr("method_name", name)
            request_payload = {
                "args": _jsonify(args),
                "kwargs": _jsonify(kwargs),
            }
            with self._logger.bind_recorder(recorder):
                try:
                    result = target(*args, **kwargs)
                except Exception as exc:
                    timing_payload = recorder.snapshot(status="failed", error_message=str(exc))
                    self._logger.save_call(
                        call_id=call_id,
                        tool_name=tool_name,
                        group_name=self._group_name,
                        method_name=name,
                        project_root=project_root,
                        request_payload=request_payload,
                        response_payload={"error": str(exc)},
                        timing_payload=timing_payload,
                        status="failed",
                        error_message=str(exc),
                    )
                    raise
                timing_payload = recorder.snapshot(status="completed", error_message=None)
                self._logger.save_call(
                    call_id=call_id,
                    tool_name=tool_name,
                    group_name=self._group_name,
                    method_name=name,
                    project_root=project_root,
                    request_payload=request_payload,
                    response_payload=_jsonify(result),
                    timing_payload=timing_payload,
                    status="completed",
                    error_message=None,
                )
                return result

        return _wrapped


def _extract_project_root(args: tuple[Any, ...], kwargs: dict[str, Any], *, service: Any) -> str | None:
    candidates = list(args)
    if "req" in kwargs:
        candidates.append(kwargs["req"])
    for item in candidates:
        project_root = getattr(item, "project_root", None)
        if project_root:
            return str(project_root)
    config = getattr(service, "config", None)
    server_cfg = getattr(config, "server", None)
    default_project_root = getattr(server_cfg, "default_project_root", None)
    return str(default_project_root) if default_project_root else None


def _normalize_view_name(value: str | None) -> str:
    text = (value or "default").strip()
    return text or "default"
