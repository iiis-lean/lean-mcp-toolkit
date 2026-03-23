from dataclasses import dataclass

from lean_mcp_toolkit.contracts.mathlib_nav import (
    MathlibNavFileOutlineRequest,
    MathlibNavReadRequest,
    MathlibNavTreeRequest,
)
from lean_mcp_toolkit.groups.mathlib_nav.client_http import MathlibNavHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True)
class _FakeHttpJsonClient:
    def post_json(self, path: str, payload: dict) -> dict:
        _ = payload
        if path == "/search/mathlib_nav/tree":
            return {"success": True, "entries": [{"kind": "file", "name": "Probe.lean"}]}
        if path == "/search/mathlib_nav/file_outline":
            return {
                "success": True,
                "target": {"file_path": "Linear/Probe.lean", "module_path": "Linear.Probe"},
                "imports": [],
                "declarations": [],
                "scope_cmds": [],
                "summary": {"total_lines": 1, "decl_count": 0},
            }
        if path == "/search/mathlib_nav/read":
            return {
                "success": True,
                "target": {"file_path": "Linear/Probe.lean", "module_path": "Linear.Probe"},
                "window": {"start_line": 1, "end_line": 1, "total_lines": 1, "truncated": False},
                "content": "1 | def x := 1",
            }
        raise AssertionError(f"unexpected path: {path}")


def test_mathlib_nav_http_client_roundtrip() -> None:
    client = MathlibNavHttpClient(
        http_config=HttpConfig(base_url="http://127.0.0.1:18080"),
        http_client=_FakeHttpJsonClient(),
    )

    tree = client.run_mathlib_nav_tree(MathlibNavTreeRequest.from_dict({}))
    assert tree.success is True
    assert tree.entries[0].name == "Probe.lean"

    outline = client.run_mathlib_nav_file_outline(
        MathlibNavFileOutlineRequest.from_dict({"target": "Linear.Probe"})
    )
    assert outline.success is True
    assert outline.target is not None
    assert outline.target.module_path == "Linear.Probe"

    read = client.run_mathlib_nav_read(MathlibNavReadRequest.from_dict({"target": "Linear/Probe.lean"}))
    assert read.success is True
    assert read.window is not None
    assert read.window.total_lines == 1
