"""Tool catalog adapters shared by remote CLI and local shell."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..app.toolkit_server import ToolkitServer
from ..transport.http import HttpConfig, HttpJsonClient


@dataclass(slots=True, frozen=True)
class ToolParamMeta:
    name: str
    type_hint: str
    description: str
    required: bool
    default_value: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolParamMeta":
        return cls(
            name=str(data.get("name") or "").strip(),
            type_hint=str(data.get("type") or "str"),
            description=str(data.get("description") or "").strip(),
            required=bool(data.get("required")),
            default_value=(
                str(data.get("default"))
                if data.get("default") is not None
                else None
            ),
        )


@dataclass(slots=True, frozen=True)
class ToolReturnMeta:
    field_path: str
    type_hint: str
    description: str
    children: tuple["ToolReturnMeta", ...] = tuple()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolReturnMeta":
        return cls(
            field_path=str(data.get("field_path") or "").strip(),
            type_hint=str(data.get("type") or "object"),
            description=str(data.get("description") or "").strip(),
            children=tuple(
                cls.from_dict(item)
                for item in list(data.get("children") or [])
                if isinstance(item, dict)
            ),
        )


@dataclass(slots=True, frozen=True)
class ToolMeta:
    group_name: str
    canonical_name: str
    raw_name: str
    aliases: tuple[str, ...]
    api_path: str
    description: str
    api_description: str
    mcp_description: str
    params: tuple[ToolParamMeta, ...]
    returns: tuple[ToolReturnMeta, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolMeta":
        aliases_raw = data.get("aliases") or []
        aliases = tuple(str(item).strip() for item in aliases_raw if str(item).strip())
        return cls(
            group_name=str(data.get("group_name") or "").strip(),
            canonical_name=str(data.get("canonical_name") or "").strip(),
            raw_name=str(data.get("raw_name") or "").strip(),
            aliases=aliases,
            api_path=str(data.get("api_path") or "").strip(),
            description=str(data.get("description") or "").strip(),
            api_description=str(data.get("api_description") or "").strip(),
            mcp_description=str(data.get("mcp_description") or "").strip(),
            params=tuple(
                ToolParamMeta.from_dict(item)
                for item in list(data.get("params") or [])
                if isinstance(item, dict)
            ),
            returns=tuple(
                ToolReturnMeta.from_dict(item)
                for item in list(data.get("returns") or [])
                if isinstance(item, dict)
            ),
        )

    def visible_aliases(self) -> tuple[str, ...]:
        if self.aliases:
            return self.aliases
        if self.canonical_name:
            return (self.canonical_name,)
        return tuple()

    def preferred_help_text(self) -> str:
        return self.api_description or self.description or self.mcp_description


class ToolCatalog(Protocol):
    def list_tools(self) -> tuple[ToolMeta, ...]:
        ...


@dataclass(slots=True)
class RemoteToolCatalog:
    http_client: HttpJsonClient

    @classmethod
    def from_http_config(cls, http_config: HttpConfig) -> "RemoteToolCatalog":
        return cls(http_client=HttpJsonClient(http_config))

    def list_tools(self) -> tuple[ToolMeta, ...]:
        data = self.http_client.get_json("/meta/tools")
        rows = data.get("tools") or []
        if not isinstance(rows, list):
            raise ValueError("expected tools list from /meta/tools")
        return tuple(ToolMeta.from_dict(item) for item in rows if isinstance(item, dict))


@dataclass(slots=True)
class LocalToolCatalog:
    server: ToolkitServer

    def list_tools(self) -> tuple[ToolMeta, ...]:
        return tuple(ToolMeta.from_dict(item) for item in self.server.describe_tools())
