from dataclasses import dataclass

from lean_mcp_toolkit.contracts.build_base import BuildWorkspaceRequest
from lean_mcp_toolkit.groups.build_base.client_http import BuildBaseHttpClient
from lean_mcp_toolkit.transport.http import HttpConfig


@dataclass(slots=True)
class _FakeHttpJsonClient:
    last_path: str | None = None
    last_payload: dict | None = None

    def post_json(self, path: str, payload: dict) -> dict:
        self.last_path = path
        self.last_payload = payload
        return {
            "success": True,
            "project_root": "/tmp/demo",
            "targets": ["Foo.Bar"],
            "target_facet": "deps",
            "jobs": 8,
            "executed_commands": [
                ["lake", "clean"],
                ["lake", "build", "-j", "8", "Foo.Bar:deps"],
            ],
            "returncode": 0,
            "timed_out": False,
            "stdout": "clean ok\n\nbuild ok",
            "stderr": "",
        }


def test_build_base_http_client_roundtrip() -> None:
    http_client = _FakeHttpJsonClient()
    client = BuildBaseHttpClient(
        http_config=HttpConfig(base_url="http://127.0.0.1:18080"),
        http_client=http_client,
    )

    resp = client.run_workspace(
        BuildWorkspaceRequest.from_dict(
            {
                "project_root": "/tmp/demo",
                "targets": ["Foo/Bar.lean"],
                "target_facet": "deps",
                "jobs": 8,
                "clean_first": True,
            }
        )
    )

    assert http_client.last_path == "/build/workspace"
    assert http_client.last_payload == {
        "project_root": "/tmp/demo",
        "targets": ["Foo/Bar.lean"],
        "target_facet": "deps",
        "jobs": 8,
        "timeout_seconds": None,
        "clean_first": True,
    }
    assert resp.success is True
    assert resp.targets == ("Foo.Bar",)
    assert resp.target_facet == "deps"
    assert resp.jobs == 8
    assert resp.executed_commands == (
        ("lake", "clean"),
        ("lake", "build", "-j", "8", "Foo.Bar:deps"),
    )
