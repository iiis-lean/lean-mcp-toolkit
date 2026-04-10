from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from fastapi.testclient import TestClient

from lean_mcp_toolkit.app import ToolkitServer
from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.groups.plugin_base import GroupToolSpec
from lean_mcp_toolkit.tool_audit import audit_stage


@dataclass(slots=True)
class _FakeAuditService:
    config: ToolkitConfig

    def run_alpha(self, payload: dict[str, object]) -> dict[str, object]:
        with audit_stage("stage_one"):
            pass
        with audit_stage("stage_two", attrs={"items": len(payload)}):
            return {
                "ok": True,
                "payload": dict(payload),
            }


@dataclass(slots=True, frozen=True)
class _FakeAuditPlugin:
    group_name: str = "fake"

    def backend_dependencies(self) -> tuple[str, ...]:
        return tuple()

    def create_local_service(self, config: ToolkitConfig, *, backends=None):
        _ = backends
        return _FakeAuditService(config=config)

    def tool_specs(self) -> tuple[GroupToolSpec, ...]:
        return (
            GroupToolSpec(
                group_name="fake",
                canonical_name="fake.alpha",
                raw_name="alpha",
                api_path="/fake/alpha",
                description="alpha tool",
            ),
        )

    def tool_handlers(self, service) -> dict[str, callable]:
        return {
            "fake.alpha": lambda payload: service.run_alpha(payload),
        }

    def register_mcp_tools(
        self,
        mcp,
        *,
        service,
        aliases_by_canonical,
        normalize_str_list,
        prune_none,
    ):
        _ = mcp
        _ = service
        _ = aliases_by_canonical
        _ = normalize_str_list
        _ = prune_none


def _audit_root(project_root: Path) -> Path:
    return project_root / ".runtime" / "toolkit"


def test_audited_service_proxy_persists_call_request_response_and_timing(
    tmp_path: Path,
) -> None:
    project_root = (tmp_path / "project").resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    cfg = ToolkitConfig.from_dict(
        {
            "server": {
                "default_project_root": str(project_root),
                "api_prefix": "/api/v1",
            },
            "groups": {
                "enabled_groups": ["fake"],
                "tool_naming_mode": "prefixed",
            },
            "audit": {
                "enabled": True,
            },
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakeAuditPlugin(),))

    result = server.dispatch_api("fake.alpha", {"value": 1, "name": "demo"})

    assert result["ok"] is True
    audit_root = _audit_root(project_root)
    calls_rows = [
        json.loads(line)
        for line in (audit_root / "calls.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(calls_rows) == 1
    call_id = calls_rows[0]["call_id"]
    assert calls_rows[0]["view"] == "default"

    call_dir = audit_root / "views" / "default" / "calls" / call_id
    meta = json.loads((call_dir / "meta.json").read_text(encoding="utf-8"))
    timing = json.loads((call_dir / "timing.json").read_text(encoding="utf-8"))
    request = json.loads((call_dir / "request.json").read_text(encoding="utf-8"))
    response = json.loads((call_dir / "response.json").read_text(encoding="utf-8"))

    assert meta["tool_name"] == "fake.run_alpha"
    assert meta["project_root"] == str(project_root)
    assert meta["status"] == "completed"
    assert meta["view"] == "default"
    assert request["args"] == [{"value": 1, "name": "demo"}]
    assert response["ok"] is True
    assert [stage["name"] for stage in timing["stages"]] == ["stage_one", "stage_two"]
    assert timing["stages"][1]["attrs"]["items"] == 2


def test_fastapi_debug_routes_expose_audit_call_metadata_and_timing(
    tmp_path: Path,
) -> None:
    project_root = (tmp_path / "project").resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    cfg = ToolkitConfig.from_dict(
        {
            "server": {
                "default_project_root": str(project_root),
                "api_prefix": "/api/v1",
            },
            "groups": {
                "enabled_groups": ["fake"],
                "tool_naming_mode": "prefixed",
            },
            "audit": {
                "enabled": True,
            },
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakeAuditPlugin(),))
    server.dispatch_api("fake.alpha", {"value": 1})

    audit_root = _audit_root(project_root)
    call_row = json.loads((audit_root / "calls.jsonl").read_text(encoding="utf-8").splitlines()[0])
    call_id = call_row["call_id"]
    assert call_row["view"] == "default"

    app = server.create_fastapi_app()
    client = TestClient(app)

    tail = client.get(
        "/api/v1/debug/calls/tail",
        params={"project_root": str(project_root), "limit": 5},
    )
    assert tail.status_code == 200
    tail_payload = tail.json()["calls"]
    assert len(tail_payload) == 1
    assert tail_payload[0]["call_id"] == call_id
    assert tail_payload[0]["view"] == "default"

    meta = client.get(
        f"/api/v1/debug/calls/{call_id}",
        params={"project_root": str(project_root)},
    )
    assert meta.status_code == 200
    assert meta.json()["meta"]["tool_name"] == "fake.run_alpha"

    timing = client.get(
        f"/api/v1/debug/calls/{call_id}/timing",
        params={"project_root": str(project_root)},
    )
    assert timing.status_code == 200
    timing_payload = timing.json()["timing"]
    assert timing_payload["tool_name"] == "fake.run_alpha"
    assert timing_payload["stages"][0]["name"] == "stage_one"


def test_fastapi_view_route_records_named_audit_view(tmp_path: Path) -> None:
    project_root = (tmp_path / "project").resolve()
    project_root.mkdir(parents=True, exist_ok=True)
    cfg = ToolkitConfig.from_dict(
        {
            "server": {
                "default_project_root": str(project_root),
                "api_prefix": "/api/v1",
            },
            "groups": {
                "enabled_groups": ["fake"],
                "tool_naming_mode": "prefixed",
            },
            "tool_views": {
                "proof": {
                    "include_tools": ["fake.alpha"],
                }
            },
            "audit": {
                "enabled": True,
            },
        }
    )
    server = ToolkitServer.from_config(cfg, plugins=(_FakeAuditPlugin(),))
    app = server.create_fastapi_app()
    client = TestClient(app)

    meta = client.get("/api/v1/views/proof/meta/tools")
    assert meta.status_code == 200
    assert [item["canonical_name"] for item in meta.json()["tools"]] == ["fake.alpha"]

    response = client.post("/api/v1/views/proof/fake/alpha", json={"value": 1})
    assert response.status_code == 200
    assert response.json()["ok"] is True

    audit_root = _audit_root(project_root)
    view_rows = [
        json.loads(line)
        for line in (audit_root / "views" / "proof" / "calls.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(view_rows) == 1
    assert view_rows[0]["view"] == "proof"
    call_id = view_rows[0]["call_id"]
    meta_payload = json.loads(
        (audit_root / "views" / "proof" / "calls" / call_id / "meta.json").read_text(encoding="utf-8")
    )
    assert meta_payload["view"] == "proof"
