from __future__ import annotations

from dataclasses import dataclass

import pytest

from lean_mcp_toolkit.app import ToolkitHttpClient
from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.groups.plugin_base import GroupToolSpec
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True, frozen=True)
class _FakeGroupClient:
    group: str = "fake"


@dataclass(slots=True, frozen=True)
class _FakePlugin:
    group_name: str = "fake"

    def create_local_service(self, config: ToolkitConfig):
        _ = config
        return object()

    def create_http_client(self, *, config: ToolkitConfig, http_config: HttpConfig):
        _ = config
        _ = http_config
        return _FakeGroupClient()

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return (
            GroupToolSpec(
                group_name="fake",
                canonical_name="fake.alpha",
                raw_name="alpha",
                api_path="/fake/alpha",
                description="alpha",
            ),
            GroupToolSpec(
                group_name="fake",
                canonical_name="fake.beta",
                raw_name="beta",
                api_path="/fake/beta",
                description="beta",
            ),
        )

    def tool_handlers(self, service) -> dict[str, callable]:
        _ = service
        return {
            "fake.alpha": lambda payload: {"tool": "fake.alpha", "payload": payload},
            "fake.beta": lambda payload: {"tool": "fake.beta", "payload": payload},
        }

    def register_mcp_tools(self, mcp, *, service, aliases_by_canonical, normalize_str_list, prune_none):
        _ = mcp
        _ = service
        _ = aliases_by_canonical
        _ = normalize_str_list
        _ = prune_none


def test_http_client_plugin_group_disabled() -> None:
    cfg = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["fake"],
                "disabled_groups": ["fake"],
                "tool_naming_mode": "prefixed",
            }
        }
    )
    client = ToolkitHttpClient.from_http_config(
        HttpConfig(base_url="http://127.0.0.1:18080"),
        config=cfg,
        plugins=(_FakePlugin(),),
    )
    assert client.available_tool_aliases() == tuple()
    assert client.available_http_routes() == tuple()
    with pytest.raises(KeyError):
        client.dispatch_api("fake.alpha", {})


def test_http_client_plugin_include_exclude_and_prefixed() -> None:
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
    client = ToolkitHttpClient.from_http_config(
        HttpConfig(base_url="http://127.0.0.1:18080"),
        config=cfg,
        plugins=(_FakePlugin(),),
    )
    assert client.available_tool_aliases() == ("fake.alpha",)
    assert client.available_http_routes() == ("/fake/alpha",)
    assert client.dispatch_api("fake.alpha", {})["tool"] == "fake.alpha"
    assert client.dispatch_api("/fake/alpha", {})["tool"] == "fake.alpha"
    with pytest.raises(KeyError):
        client.dispatch_api("fake.beta", {})


def test_http_client_plugin_naming_mode_raw_and_both() -> None:
    cfg_raw = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["fake"],
                "tool_naming_mode": "raw",
            }
        }
    )
    client_raw = ToolkitHttpClient.from_http_config(
        HttpConfig(base_url="http://127.0.0.1:18080"),
        config=cfg_raw,
        plugins=(_FakePlugin(),),
    )
    assert client_raw.available_tool_aliases() == ("alpha", "beta")
    assert client_raw.dispatch_api("alpha", {})["tool"] == "fake.alpha"
    with pytest.raises(KeyError):
        client_raw.dispatch_api("fake.alpha", {})
    assert client_raw.dispatch_api("/fake/alpha", {})["tool"] == "fake.alpha"

    cfg_both = ToolkitConfig.from_dict(
        {
            "groups": {
                "enabled_groups": ["fake"],
                "tool_naming_mode": "both",
            }
        }
    )
    client_both = ToolkitHttpClient.from_http_config(
        HttpConfig(base_url="http://127.0.0.1:18080"),
        config=cfg_both,
        plugins=(_FakePlugin(),),
    )
    assert set(client_both.available_tool_aliases()) == {"alpha", "beta", "fake.alpha", "fake.beta"}
    assert client_both.dispatch_api("fake.beta", {})["tool"] == "fake.beta"
    assert client_both.dispatch_api("beta", {})["tool"] == "fake.beta"
