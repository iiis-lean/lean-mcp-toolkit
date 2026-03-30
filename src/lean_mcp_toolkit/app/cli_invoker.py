"""Tool invokers used by remote CLI and local shell."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .toolkit_client import ToolkitHttpClient
from .toolkit_server import ToolkitServer


class ToolInvoker(Protocol):
    def invoke(self, tool_ref: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass(slots=True)
class HttpToolInvoker:
    client: ToolkitHttpClient

    def invoke(self, tool_ref: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.client.dispatch_api(tool_ref, payload)


@dataclass(slots=True)
class LocalToolInvoker:
    server: ToolkitServer

    def invoke(self, tool_ref: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.server.dispatch_api(tool_ref, payload)
