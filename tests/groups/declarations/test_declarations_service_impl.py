from pathlib import Path

from lean_mcp_toolkit.backends.declarations import (
    DeclarationsBackendRequest,
    DeclarationsBackendResponse,
)
from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.declarations import (
    DeclarationExtractRequest,
    DeclarationLocateRequest,
)
from lean_mcp_toolkit.groups.declarations.service_impl import DeclarationsServiceImpl


class _FakePos:
    def __init__(self, line: int, column: int):
        self.line = line
        self.column = column


class _FakeRange:
    def __init__(self, start: _FakePos, finish: _FakePos):
        self.start = start
        self.finish = finish


class _FakeDocString:
    def __init__(self, content: str, range_obj: _FakeRange):
        self.content = content
        self.range = range_obj


class _FakeModifiers:
    def __init__(self, doc_string: _FakeDocString | None):
        self.doc_string = doc_string


class _FakeDecl:
    def __init__(self) -> None:
        self.name = "foo"
        self.full_name = "A.B.foo"
        self.kind = "theorem"
        self.pp = "/-- foo doc -/\ntheorem foo : True := by trivial"
        self.range = _FakeRange(start=_FakePos(1, 0), finish=_FakePos(1, 29))
        self.signature = type(
            "Sig",
            (),
            {
                "pp": "True",
                "range": _FakeRange(start=_FakePos(1, 14), finish=_FakePos(1, 18)),
            },
        )()
        self.value = type(
            "Val",
            (),
            {
                "pp": ":= by trivial",
                "range": _FakeRange(start=_FakePos(1, 19), finish=_FakePos(1, 32)),
            },
        )()
        self.modifiers = _FakeModifiers(
            doc_string=_FakeDocString(
                content="/-- foo doc -/",
                range_obj=_FakeRange(start=_FakePos(2, 0), finish=_FakePos(2, 14)),
            )
        )


class _FakeBackend:
    backend_name = "fake"

    def __init__(self) -> None:
        self.last_req: DeclarationsBackendRequest | None = None

    def extract(self, req: DeclarationsBackendRequest) -> DeclarationsBackendResponse:
        self.last_req = req
        return DeclarationsBackendResponse(
            success=True,
            declarations=(_FakeDecl(),),
            messages=tuple(),
            sorries=tuple(),
        )


class _FakeLspClient:
    def __init__(self, target_uri: str = "file:///tmp/project/A/B.lean") -> None:
        self.last_opened: str | None = None
        self.target_uri = target_uri

    def open_file(self, rel_path: str) -> None:
        self.last_opened = rel_path

    def get_file_content(self, rel_path: str) -> str:
        _ = rel_path
        return "import A.B\n\n#check foo\n"

    def get_declarations(self, rel_path: str, line: int, column: int):
        _ = rel_path, line, column
        return [
            {
                "targetUri": self.target_uri,
                "targetRange": {
                    "start": {"line": 0, "character": 8},
                    "end": {"line": 0, "character": 11},
                },
                "targetSelectionRange": {
                    "start": {"line": 0, "character": 8},
                    "end": {"line": 0, "character": 11},
                },
            }
        ]

    def get_definitions(self, rel_path: str, line: int, column: int):
        _ = rel_path, line, column
        return []


class _FakeLspClientManager:
    def __init__(self, client: _FakeLspClient):
        self.client = client

    def get_client(self, project_root: Path) -> _FakeLspClient:
        _ = project_root
        return self.client


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_declarations_extract_normalizes_target_and_calls_backend(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "B.lean", "theorem foo : True := by trivial\n")
    backend = _FakeBackend()
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "declarations": {
                "default_backend": "lean_interact",
                "default_include_value": True,
                "default_timeout_seconds": 15,
            },
        }
    )
    svc = DeclarationsServiceImpl(config=cfg, backends={"lean_interact": backend})

    resp = svc.extract(DeclarationExtractRequest.from_dict({"target": "A/B.lean"}))

    assert resp.success is True
    assert resp.total_declarations == 1
    assert resp.declarations[0].name == "A.B.foo"
    assert resp.declarations[0].signature == "True"
    assert resp.declarations[0].value == ":= by trivial"
    assert resp.declarations[0].docstring == "/-- foo doc -/"
    assert backend.last_req is not None
    assert backend.last_req.target_dot == "A.B"
    assert backend.last_req.timeout_seconds == 15


def test_declarations_extract_invalid_target_returns_failure(tmp_path: Path) -> None:
    cfg = ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}})
    svc = DeclarationsServiceImpl(config=cfg)

    resp = svc.extract(DeclarationExtractRequest.from_dict({"target": "Missing.File"}))

    assert resp.success is False
    assert resp.total_declarations == 0
    assert resp.error_message is not None


def test_declarations_extract_hides_value_when_include_value_disabled(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "B.lean", "theorem foo : True := by trivial\n")
    backend = _FakeBackend()
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "declarations": {
                "default_backend": "lean_interact",
                "default_include_value": False,
                "default_timeout_seconds": 15,
            },
        }
    )
    svc = DeclarationsServiceImpl(config=cfg, backends={"lean_interact": backend})

    resp = svc.extract(DeclarationExtractRequest.from_dict({"target": "A/B.lean"}))

    assert resp.success is True
    assert resp.total_declarations == 1
    assert resp.declarations[0].signature == "True"
    assert resp.declarations[0].value is None


def test_declarations_extract_invalid_project_root_returns_failure(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "B.lean", "theorem foo : True := by trivial\n")
    cfg = ToolkitConfig()
    svc = DeclarationsServiceImpl(config=cfg)

    resp = svc.extract(
        DeclarationExtractRequest.from_dict(
            {
                "project_root": str(tmp_path / "does-not-exist"),
                "target": "A.B",
            }
        )
    )

    assert resp.success is False
    assert resp.error_message is not None


def test_declarations_locate_matches_declaration_content(tmp_path: Path) -> None:
    _write(tmp_path / "A" / "B.lean", "theorem foo : True := by trivial\n")
    backend = _FakeBackend()
    lsp_client = _FakeLspClient(target_uri=(tmp_path / "A" / "B.lean").resolve().as_uri())
    lsp_manager = _FakeLspClientManager(lsp_client)
    cfg = ToolkitConfig.from_dict(
        {
            "server": {"default_project_root": str(tmp_path)},
            "declarations": {
                "default_backend": "lean_interact",
                "default_include_value": True,
                "default_timeout_seconds": 15,
            },
        }
    )
    svc = DeclarationsServiceImpl(
        config=cfg,
        backends={"lean_interact": backend},
        lsp_client_manager=lsp_manager,  # type: ignore[arg-type]
    )

    resp = svc.locate(
        DeclarationLocateRequest.from_dict(
            {
                "source_file": "A/B.lean",
                "symbol": "foo",
            }
        )
    )

    assert resp.success is True
    assert resp.source_pos is not None
    assert resp.source_pos.line == 2
    assert resp.source_pos.column == 7
    assert resp.target_file_path == str((tmp_path / "A" / "B.lean").resolve())
    assert resp.target_range is not None
    assert resp.target_range.start.line == 0
    assert resp.target_range.start.column == 8
    assert resp.matched_declaration is not None
    assert resp.matched_declaration.name == "A.B.foo"
    assert lsp_client.last_opened == "A/B.lean"
