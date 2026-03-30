from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

from lean_mcp_toolkit.app.cli_catalog import ToolMeta, ToolParamMeta
from lean_mcp_toolkit.app.cli_shared import execute_cli_tokens


@dataclass(slots=True)
class _FakeCatalog:
    tools: tuple[ToolMeta, ...]

    def list_tools(self) -> tuple[ToolMeta, ...]:
        return self.tools


@dataclass(slots=True)
class _FakeInvoker:
    calls: list[tuple[str, dict]]

    def invoke(self, tool_ref: str, payload: dict) -> dict:
        self.calls.append((tool_ref, payload))
        return {"tool_ref": tool_ref, "payload": payload}


def _tool(*, canonical: str, aliases: tuple[str, ...], api_path: str, params: tuple[ToolParamMeta, ...] = tuple()) -> ToolMeta:
    return ToolMeta(
        group_name=canonical.split(".")[0],
        canonical_name=canonical,
        raw_name=canonical.split(".")[-1],
        aliases=aliases,
        api_path=api_path,
        description=f"{canonical} description",
        api_description=f"{canonical} api description",
        mcp_description=f"{canonical} mcp description",
        params=params,
        returns=tuple(),
    )


def test_tools_command_renders_alias_tree() -> None:
    catalog = _FakeCatalog(
        (
            _tool(canonical="diagnostics.lint", aliases=("diagnostics.lint",), api_path="/diagnostics/lint"),
            _tool(canonical="diagnostics.lint.no_sorry", aliases=("diagnostics.lint.no_sorry",), api_path="/diagnostics/lint/no_sorry"),
            _tool(canonical="lsp.hover", aliases=("lsp.hover_info",), api_path="/lsp/hover"),
        )
    )
    out = StringIO()
    err = StringIO()

    code = execute_cli_tokens(
        ["tools"],
        prog="lean-cli-toolkit",
        catalog=catalog,
        invoker=_FakeInvoker([]),
        stdout=out,
        stderr=err,
    )

    assert code == 0
    text = out.getvalue()
    assert "diagnostics" in text
    assert "lint" in text
    assert "no-sorry" in text
    assert "lsp" in text
    assert "hover-info" in text


def test_tool_command_maps_cli_args_to_payload() -> None:
    catalog = _FakeCatalog(
        (
            _tool(
                canonical="diagnostics.lint",
                aliases=("diagnostics.lint",),
                api_path="/diagnostics/lint",
                params=(
                    ToolParamMeta("project_root", "str | null", "root", False, None),
                    ToolParamMeta("targets", "list[str] | str | null", "targets", False, None),
                    ToolParamMeta("include_content", "bool | null", "content", False, None),
                ),
            ),
        )
    )
    invoker = _FakeInvoker([])
    out = StringIO()
    err = StringIO()

    code = execute_cli_tokens(
        [
            "diagnostics",
            "lint",
            "--project-root",
            "/tmp/demo",
            "--targets",
            "A.lean",
            "--targets",
            "B.lean",
            "--include-content",
        ],
        prog="lean-cli-toolkit",
        catalog=catalog,
        invoker=invoker,
        stdout=out,
        stderr=err,
    )

    assert code == 0
    assert invoker.calls == [
        (
            "/diagnostics/lint",
            {
                "project_root": "/tmp/demo",
                "targets": ["A.lean", "B.lean"],
                "include_content": True,
            },
        )
    ]
    assert '"project_root": "/tmp/demo"' in out.getvalue()


def test_tool_help_uses_dynamic_spec() -> None:
    catalog = _FakeCatalog(
        (
            _tool(
                canonical="lsp.hover",
                aliases=("lsp.hover_info",),
                api_path="/lsp/hover",
                params=(
                    ToolParamMeta("file_path", "str", "Lean file path", True, None),
                    ToolParamMeta("line", "int", "Line number", True, None),
                ),
            ),
        )
    )
    out = StringIO()
    err = StringIO()

    code = execute_cli_tokens(
        ["lsp", "hover-info", "--help"],
        prog="lean-cli-toolkit",
        catalog=catalog,
        invoker=_FakeInvoker([]),
        stdout=out,
        stderr=err,
    )

    assert code == 0
    text = out.getvalue()
    assert "lsp.hover api description" in text
    assert "--file-path" in text
    assert "--line" in text
