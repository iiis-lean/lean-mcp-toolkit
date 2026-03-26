from dataclasses import dataclass
from pathlib import Path

from lean_mcp_toolkit.backends.declarations import (
    DeclarationsBackendRequest,
    LeanInteractDeclarationsBackend,
)
from lean_mcp_toolkit.config import LeanInteractBackendConfig, ToolchainConfig


@dataclass(slots=True)
class _FakePos:
    line: int
    column: int


@dataclass(slots=True)
class _FakeRange:
    start: _FakePos
    finish: _FakePos


@dataclass(slots=True)
class _FakeDocString:
    content: str
    range: _FakeRange


@dataclass(slots=True)
class _FakeModifiers:
    doc_string: _FakeDocString | None = None


@dataclass(slots=True)
class _FakeSignature:
    pp: str
    range: _FakeRange


@dataclass(slots=True)
class _FakeValue:
    pp: str
    range: _FakeRange


@dataclass(slots=True)
class _FakeDecl:
    name: str
    full_name: str
    kind: str
    pp: str
    range: _FakeRange
    modifiers: _FakeModifiers
    signature: _FakeSignature
    value: _FakeValue | None = None


@dataclass(slots=True)
class _FakeMessage:
    severity: str
    data: str


@dataclass(slots=True)
class _FakeSorry:
    goal: str


class _FakeResponse:
    def __init__(
        self,
        *,
        declarations: list[_FakeDecl],
        messages: list[_FakeMessage] | None = None,
        sorries: list[_FakeSorry] | None = None,
        has_errors: bool = False,
    ):
        self.declarations = declarations
        self.messages = messages or []
        self.sorries = sorries or []
        self._has_errors = has_errors

    def has_errors(self) -> bool:
        return self._has_errors


@dataclass(slots=True)
class _FakeFileCommand:
    path: str
    declarations: bool


class _FakeLeanError:
    def __init__(self, message: str):
        self.message = message


class _FakeLocalProject:
    created: list[dict] = []

    def __init__(self, *, directory: str, auto_build: bool, lake_path: str):
        self.directory = directory
        self.auto_build = auto_build
        self.lake_path = lake_path
        self.__class__.created.append(
            {
                "directory": directory,
                "auto_build": auto_build,
                "lake_path": lake_path,
            }
        )


class _FakeLeanREPLConfig:
    created: list[dict] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__class__.created.append(kwargs)


class _FakeLeanServer:
    created: list[object] = []
    last_run: dict | None = None
    response_factory = staticmethod(
        lambda: _FakeResponse(
            declarations=[],
            messages=[],
            sorries=[],
        )
    )

    def __init__(self, config):
        self.config = config
        self.__class__.created.append(config)

    def run(self, file_command, timeout=None):
        self.__class__.last_run = {"file_command": file_command, "timeout": timeout}
        return self.__class__.response_factory()


class _FakeAutoLeanServer(_FakeLeanServer):
    created: list[object] = []


def _fake_module_dict() -> dict:
    return {
        "LeanREPLConfig": _FakeLeanREPLConfig,
        "LeanServer": _FakeLeanServer,
        "AutoLeanServer": _FakeAutoLeanServer,
        "LocalProject": _FakeLocalProject,
        "FileCommand": _FakeFileCommand,
        "LeanError": _FakeLeanError,
    }


def _reset_fakes() -> None:
    _FakeLocalProject.created = []
    _FakeLeanREPLConfig.created = []
    _FakeLeanServer.created = []
    _FakeLeanServer.last_run = None
    _FakeAutoLeanServer.created = []
    _FakeLeanServer.response_factory = staticmethod(
        lambda: _FakeResponse(
            declarations=[],
            messages=[],
            sorries=[],
        )
    )
    _FakeAutoLeanServer.response_factory = staticmethod(
        lambda: _FakeResponse(
            declarations=[],
            messages=[],
            sorries=[],
        )
    )


def _sample_decl() -> _FakeDecl:
    return _FakeDecl(
        name="foo",
        full_name="A.B.foo",
        kind="theorem",
        pp="theorem foo : True := by trivial",
        range=_FakeRange(start=_FakePos(1, 0), finish=_FakePos(1, 29)),
        modifiers=_FakeModifiers(
            doc_string=_FakeDocString(
                content="/-- foo doc -/",
                range=_FakeRange(start=_FakePos(1, 0), finish=_FakePos(1, 14)),
            )
        ),
        signature=_FakeSignature(
            pp="True",
            range=_FakeRange(start=_FakePos(1, 13), finish=_FakePos(1, 17)),
        ),
        value=_FakeValue(
            pp=":= by trivial",
            range=_FakeRange(start=_FakePos(1, 18), finish=_FakePos(1, 29)),
        ),
    )


def test_lean_interact_backend_returns_raw_declarations_and_reuses_server(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _reset_fakes()
    backend = LeanInteractDeclarationsBackend(
        toolchain_config=ToolchainConfig(lake_bin="lake-custom"),
        backend_config=LeanInteractBackendConfig(
            project_auto_build=True,
            build_repl=False,
            enable_incremental_optimization=False,
            enable_parallel_elaboration=False,
            verbose=True,
        ),
    )
    monkeypatch.setattr(backend, "_load_lean_interact", lambda: _fake_module_dict())
    _FakeLeanServer.response_factory = staticmethod(
        lambda: _FakeResponse(
            declarations=[_sample_decl()],
            messages=[_FakeMessage(severity="info", data="ok")],
            sorries=[_FakeSorry(goal="?m_1")],
            has_errors=False,
        )
    )

    req = DeclarationsBackendRequest(
        project_root=tmp_path,
        target_dot="A.B",
        timeout_seconds=12,
    )
    first = backend.extract(req)
    second = backend.extract(req)

    assert first.success is True
    assert first.error_message is None
    assert len(first.declarations) == 1
    assert first.declarations[0].full_name == "A.B.foo"
    assert len(first.messages) == 1
    assert first.messages[0].data == "ok"
    assert len(first.sorries) == 1
    assert first.sorries[0].goal == "?m_1"
    assert _FakeLeanServer.last_run is not None
    assert _FakeLeanServer.last_run["file_command"].path == "A/B.lean"
    assert _FakeLeanServer.last_run["timeout"] == 12.0
    assert len(_FakeLocalProject.created) == 1
    assert _FakeLocalProject.created[0]["directory"] == str(tmp_path)
    assert _FakeLocalProject.created[0]["auto_build"] is True
    assert _FakeLocalProject.created[0]["lake_path"] == "lake-custom"
    assert len(_FakeLeanREPLConfig.created) == 1
    assert _FakeLeanREPLConfig.created[0]["build_repl"] is False
    assert _FakeLeanREPLConfig.created[0]["enable_incremental_optimization"] is False
    assert _FakeLeanREPLConfig.created[0]["enable_parallel_elaboration"] is False
    assert _FakeLeanREPLConfig.created[0]["verbose"] is True
    assert second.success is True
    assert len(_FakeLeanServer.created) == 1


def test_lean_interact_backend_omits_optional_config_values_when_unset(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _reset_fakes()
    backend = LeanInteractDeclarationsBackend(
        toolchain_config=ToolchainConfig(),
        backend_config=LeanInteractBackendConfig(
            cache_dir=None,
            repl_rev=None,
            repl_git=None,
        ),
    )
    monkeypatch.setattr(backend, "_load_lean_interact", lambda: _fake_module_dict())

    resp = backend.extract(
        DeclarationsBackendRequest(
            project_root=tmp_path,
            target_dot="A.B",
            timeout_seconds=None,
        )
    )

    assert resp.success is True
    assert len(_FakeLeanREPLConfig.created) == 1
    assert "cache_dir" not in _FakeLeanREPLConfig.created[0]
    assert "repl_rev" not in _FakeLeanREPLConfig.created[0]
    assert "repl_git" not in _FakeLeanREPLConfig.created[0]


def test_lean_interact_backend_auto_maps_project_lean_version_to_repl_rev(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _reset_fakes()
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.28.0\n", encoding="utf-8")
    backend = LeanInteractDeclarationsBackend(
        toolchain_config=ToolchainConfig(),
        backend_config=LeanInteractBackendConfig(
            repl_rev=None,
            repl_git=None,
            cache_dir=None,
        ),
    )
    monkeypatch.setattr(backend, "_load_lean_interact", lambda: _fake_module_dict())

    resp = backend.extract(
        DeclarationsBackendRequest(
            project_root=tmp_path,
            target_dot="A.B",
            timeout_seconds=None,
        )
    )

    assert resp.success is True
    assert len(_FakeLeanREPLConfig.created) == 1
    assert _FakeLeanREPLConfig.created[0]["repl_rev"] == "v1.3.14"
    assert _FakeLeanREPLConfig.created[0]["force_pull_repl"] is True


def test_lean_interact_backend_uses_auto_server_when_enabled(monkeypatch, tmp_path: Path) -> None:
    _reset_fakes()
    backend = LeanInteractDeclarationsBackend(
        toolchain_config=ToolchainConfig(),
        backend_config=LeanInteractBackendConfig(use_auto_server=True),
    )
    monkeypatch.setattr(backend, "_load_lean_interact", lambda: _fake_module_dict())

    resp = backend.extract(
        DeclarationsBackendRequest(
            project_root=tmp_path,
            target_dot="A.B",
            timeout_seconds=None,
        )
    )

    assert resp.success is True
    assert len(_FakeAutoLeanServer.created) == 1
    assert len(_FakeLeanServer.created) == 0


def test_lean_interact_backend_returns_structured_failure_for_lean_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _reset_fakes()
    backend = LeanInteractDeclarationsBackend(
        toolchain_config=ToolchainConfig(),
        backend_config=LeanInteractBackendConfig(),
    )
    monkeypatch.setattr(backend, "_load_lean_interact", lambda: _fake_module_dict())
    _FakeLeanServer.response_factory = staticmethod(lambda: _FakeLeanError("boom"))

    resp = backend.extract(
        DeclarationsBackendRequest(
            project_root=tmp_path,
            target_dot="A.B",
            timeout_seconds=None,
        )
    )

    assert resp.success is False
    assert resp.error_message == "boom"
    assert len(resp.declarations) == 0
    assert len(resp.messages) == 0
    assert len(resp.sorries) == 0


def test_lean_interact_backend_returns_structured_failure_for_response_errors(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _reset_fakes()
    backend = LeanInteractDeclarationsBackend(
        toolchain_config=ToolchainConfig(),
        backend_config=LeanInteractBackendConfig(),
    )
    monkeypatch.setattr(backend, "_load_lean_interact", lambda: _fake_module_dict())
    _FakeLeanServer.response_factory = staticmethod(
        lambda: _FakeResponse(
            declarations=[_sample_decl()],
            messages=[_FakeMessage(severity="error", data="bad declaration")],
            sorries=[_FakeSorry(goal="?m_1")],
            has_errors=True,
        )
    )

    resp = backend.extract(
        DeclarationsBackendRequest(
            project_root=tmp_path,
            target_dot="A.B",
            timeout_seconds=None,
        )
    )

    assert resp.success is False
    assert resp.error_message == "bad declaration"
    assert len(resp.declarations) == 1
    assert len(resp.messages) == 1
    assert len(resp.sorries) == 1


def test_lean_interact_backend_includes_exception_type_for_empty_message(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _reset_fakes()
    backend = LeanInteractDeclarationsBackend(
        toolchain_config=ToolchainConfig(),
        backend_config=LeanInteractBackendConfig(),
    )
    monkeypatch.setattr(backend, "_load_lean_interact", lambda: _fake_module_dict())

    def _boom(_: Path) -> object:
        raise AssertionError()

    monkeypatch.setattr(backend, "_create_server", _boom)

    resp = backend.extract(
        DeclarationsBackendRequest(
            project_root=tmp_path,
            target_dot="A.B",
            timeout_seconds=None,
        )
    )

    assert resp.success is False
    assert resp.error_message == "lean_interact execution failed: AssertionError"
