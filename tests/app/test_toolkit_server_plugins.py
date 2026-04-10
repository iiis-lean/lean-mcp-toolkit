from __future__ import annotations

from dataclasses import dataclass
import inspect

import pytest

from lean_mcp_toolkit.app import ToolkitServer
from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.groups import builtin_group_plugins
from lean_mcp_toolkit.groups.plugin_base import GroupToolSpec


@dataclass(slots=True, frozen=True)
class _FakePlugin:
    group_name: str = "fake"

    def backend_dependencies(self) -> tuple[str, ...]:
        return tuple()

    def create_local_service(self, config: ToolkitConfig, *, backends=None):
        _ = config
        _ = backends
        return object()

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return (
            GroupToolSpec(
                group_name="fake",
                canonical_name="fake.alpha",
                raw_name="alpha",
                api_path="/fake/alpha",
                description="alpha tool",
                tags=("proof", "read_only"),
            ),
            GroupToolSpec(
                group_name="fake",
                canonical_name="fake.beta",
                raw_name="beta",
                api_path="/fake/beta",
                description="beta tool",
                tags=("search", "expensive"),
            ),
        )

    def tool_handlers(self, service) -> dict[str, callable]:
        _ = service
        return {
            "fake.alpha": lambda payload: {"tool": "fake.alpha", "payload": payload},
            "fake.beta": lambda payload: {"tool": "fake.beta", "payload": payload},
        }

    def register_mcp_tools(self, mcp, *, service, aliases_by_canonical, normalize_str_list, prune_none):
        _ = service
        _ = normalize_str_list
        _ = prune_none
        for canonical_name, aliases in aliases_by_canonical.items():
            for alias in aliases:
                @mcp.tool(name=alias, description=canonical_name)
                async def _fake_tool():
                    return {"tool": canonical_name}


def test_plugin_group_disabled_removes_all_tools() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["fake"],
                "disabled_groups": ["fake"],
                "tool_naming_mode": "prefixed",
            }
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakePlugin(),))

    assert server.available_tool_aliases() == tuple()
    assert server.available_http_routes() == tuple()
    with pytest.raises(KeyError):
        server.dispatch_api("/fake/alpha", {})
    with pytest.raises(KeyError):
        server.dispatch_api("fake.alpha", {})


def test_plugin_include_exclude_filters_tools() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["fake"],
                "include_tools": ["fake.alpha", "beta"],
                "exclude_tools": ["fake.beta"],
                "tool_naming_mode": "prefixed",
            }
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakePlugin(),))

    assert server.available_tool_aliases() == ("fake.alpha",)
    assert server.available_http_routes() == ("/fake/alpha",)
    assert server.dispatch_api("fake.alpha", {})["tool"] == "fake.alpha"
    assert server.dispatch_api("/fake/alpha", {})["tool"] == "fake.alpha"
    with pytest.raises(KeyError):
        server.dispatch_api("fake.beta", {})
    with pytest.raises(KeyError):
        server.dispatch_api("/fake/beta", {})


def test_plugin_tool_naming_mode_raw() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["fake"],
                "tool_naming_mode": "raw",
            }
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakePlugin(),))

    assert server.available_tool_aliases() == ("alpha", "beta")
    assert server.dispatch_api("alpha", {})["tool"] == "fake.alpha"
    with pytest.raises(KeyError):
        server.dispatch_api("fake.alpha", {})
    assert server.dispatch_api("/fake/alpha", {})["tool"] == "fake.alpha"


def test_plugin_tool_naming_mode_both_and_unknown_group_ignored() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["unknown_group", "fake"],
                "tool_naming_mode": "both",
            }
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakePlugin(),))

    assert set(server.available_tool_aliases()) == {"fake.alpha", "fake.beta", "alpha", "beta"}
    assert server.dispatch_api("fake.beta", {})["tool"] == "fake.beta"
    assert server.dispatch_api("beta", {})["tool"] == "fake.beta"


def test_plugin_named_tool_view_filters_tools_by_tags() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["fake"],
                "tool_naming_mode": "prefixed",
            },
            "tool_views": {
                "proof": {
                    "include_tags": ["proof"],
                    "exclude_tags": ["expensive"],
                    "tool_naming_mode": "raw",
                }
            },
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakePlugin(),))

    assert server.available_tool_aliases() == ("fake.alpha", "fake.beta")
    assert server.available_tool_aliases(view_name="proof") == ("alpha",)
    assert server.available_http_routes(view_name="proof") == ("/fake/alpha",)
    assert server.describe_tools(view_name="proof")[0]["tags"] == ["proof", "read_only"]
    assert server.dispatch_api("alpha", {}, view_name="proof")["tool"] == "fake.alpha"
    with pytest.raises(KeyError):
        server.dispatch_api("beta", {}, view_name="proof")


def test_named_tool_view_registers_mcp_alias_subset() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["fake"],
                "tool_naming_mode": "prefixed",
            },
            "tool_views": {
                "search": {
                    "include_tags": ["search"],
                }
            },
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakePlugin(),))
    mcp = _CaptureMCP()

    server._register_mcp_tools(mcp, view_name="search")

    assert set(mcp.handlers) == {"fake.beta"}


class _CaptureMCP:
    def __init__(self) -> None:
        self.handlers: dict[str, object] = {}

    def tool(self, *, name: str, description: str):
        _ = description

        def _decorator(fn):
            self.handlers[name] = fn
            return fn

        return _decorator


def test_builtin_plugins_register_async_mcp_tools() -> None:
    def _normalize_str_list(value):
        if value is None or isinstance(value, list):
            return value
        return [value]

    def _prune_none(payload: dict[str, object]) -> dict[str, object]:
        return {k: v for k, v in payload.items() if v is not None}

    for plugin in builtin_group_plugins():
        mcp = _CaptureMCP()
        aliases_by_canonical = {
            spec.canonical_name: (spec.canonical_name,)
            for spec in plugin.tool_specs()
        }
        plugin.register_mcp_tools(
            mcp,
            service=object(),
            aliases_by_canonical=aliases_by_canonical,
            normalize_str_list=_normalize_str_list,
            prune_none=_prune_none,
        )
        assert mcp.handlers, plugin.group_name
        assert all(
            inspect.iscoroutinefunction(handler)
            for handler in mcp.handlers.values()
        ), plugin.group_name
        if plugin.group_name == "lsp_core":
            assert "lsp.run_snippet" in mcp.handlers
        if plugin.group_name == "lsp_assist":
            assert "lsp.run_snippet" not in mcp.handlers
