from dataclasses import dataclass
from pathlib import Path

from lean_mcp_toolkit.backends.lean import CommandResult
from lean_mcp_toolkit.config import ToolkitConfig
from lean_mcp_toolkit.contracts.build_base import BuildWorkspaceRequest
from lean_mcp_toolkit.groups.build_base.service_impl import BuildBaseServiceImpl


@dataclass(slots=True, frozen=True)
class _FakeResolvedTargets:
    modules: tuple[str, ...]

    def module_dots(self) -> tuple[str, ...]:
        return self.modules


@dataclass(slots=True)
class _FakeResolver:
    resolved_targets: tuple[str, ...]
    calls: list[tuple[Path, tuple[str, ...]]] | None = None

    def __post_init__(self) -> None:
        if self.calls is None:
            self.calls = []

    def resolve(
        self,
        *,
        project_root: str | Path,
        targets: tuple[str, ...] | list[str] | None,
    ) -> _FakeResolvedTargets:
        self.calls.append((Path(project_root).resolve(), tuple(targets or ())))
        return _FakeResolvedTargets(self.resolved_targets)


@dataclass(slots=True)
class _FakeRuntime:
    clean_result: CommandResult
    build_result: CommandResult
    clean_calls: list[tuple[Path, int | None]] | None = None
    build_calls: list[tuple[Path, tuple[str, ...], str | None, int | None, int | None]] | None = None

    def __post_init__(self) -> None:
        if self.clean_calls is None:
            self.clean_calls = []
        if self.build_calls is None:
            self.build_calls = []

    def run_lake_clean(
        self,
        *,
        project_root: Path,
        timeout_s: int | None,
    ) -> CommandResult:
        self.clean_calls.append((project_root.resolve(), timeout_s))
        return self.clean_result

    def run_lake_build(
        self,
        *,
        project_root: Path,
        module_targets: tuple[str, ...],
        target_facet: str | None = None,
        timeout_s: int | None,
        jobs: int | None,
    ) -> CommandResult:
        self.build_calls.append(
            (project_root.resolve(), module_targets, target_facet, timeout_s, jobs)
        )
        return self.build_result


def test_build_base_service_builds_workspace_with_defaults(tmp_path: Path) -> None:
    runtime = _FakeRuntime(
        clean_result=CommandResult(args=("lake", "clean"), returncode=0, stdout="", stderr=""),
        build_result=CommandResult(
            args=("lake", "build"),
            returncode=0,
            stdout="build ok\n",
            stderr="",
        ),
    )
    resolver = _FakeResolver(resolved_targets=("Ignored.Module",))
    svc = BuildBaseServiceImpl(
        config=ToolkitConfig.from_dict(
            {
                "server": {"default_project_root": str(tmp_path)},
                "build_base": {"default_timeout_seconds": 17, "default_jobs": 6},
            }
        ),
        runtime=runtime,
        resolver=resolver,
    )

    resp = svc.run_workspace(BuildWorkspaceRequest.from_dict({}))

    assert resp.success is True
    assert resp.project_root == str(tmp_path.resolve())
    assert resp.targets == tuple()
    assert resp.jobs == 6
    assert resp.executed_commands == (("lake", "build"),)
    assert resp.stdout == "build ok"
    assert resolver.calls == []
    assert runtime.clean_calls == []
    assert runtime.build_calls == [
        (tmp_path.resolve(), tuple(), None, 17, 6),
    ]


def test_build_base_service_supports_clean_targets_and_facet(tmp_path: Path) -> None:
    runtime = _FakeRuntime(
        clean_result=CommandResult(
            args=("lake", "clean"),
            returncode=0,
            stdout="clean ok\n",
            stderr="",
        ),
        build_result=CommandResult(
            args=("lake", "build", "-j", "8", "Foo.Bar:deps"),
            returncode=0,
            stdout="build ok\n",
            stderr="warn only\n",
        ),
    )
    resolver = _FakeResolver(resolved_targets=("Foo.Bar",))
    svc = BuildBaseServiceImpl(
        config=ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}}),
        runtime=runtime,
        resolver=resolver,
    )

    resp = svc.run_workspace(
        BuildWorkspaceRequest.from_dict(
            {
                "targets": ["Foo/Bar.lean"],
                "target_facet": "deps",
                "jobs": 8,
                "timeout_seconds": 31,
                "clean_first": True,
            }
        )
    )

    assert resp.success is True
    assert resp.targets == ("Foo.Bar",)
    assert resp.target_facet == "deps"
    assert resp.jobs == 8
    assert resp.executed_commands == (
        ("lake", "clean"),
        ("lake", "build", "-j", "8", "Foo.Bar:deps"),
    )
    assert resp.stdout == "clean ok\n\nbuild ok"
    assert resp.stderr == "warn only"
    assert resolver.calls == [(tmp_path.resolve(), ("Foo/Bar.lean",))]
    assert runtime.clean_calls == [(tmp_path.resolve(), 31)]
    assert runtime.build_calls == [
        (tmp_path.resolve(), ("Foo.Bar",), "deps", 31, 8),
    ]


def test_build_base_service_rejects_facet_without_targets(tmp_path: Path) -> None:
    runtime = _FakeRuntime(
        clean_result=CommandResult(args=("lake", "clean"), returncode=0, stdout="", stderr=""),
        build_result=CommandResult(args=("lake", "build"), returncode=0, stdout="", stderr=""),
    )
    svc = BuildBaseServiceImpl(
        config=ToolkitConfig.from_dict({"server": {"default_project_root": str(tmp_path)}}),
        runtime=runtime,
        resolver=_FakeResolver(resolved_targets=tuple()),
    )

    resp = svc.run_workspace(
        BuildWorkspaceRequest.from_dict({"target_facet": "deps"})
    )

    assert resp.success is False
    assert resp.error_message == "target_facet requires explicit targets"
    assert resp.returncode == 2
    assert resp.executed_commands == tuple()
    assert runtime.clean_calls == []
    assert runtime.build_calls == []


def test_build_base_service_stops_after_clean_failure(tmp_path: Path) -> None:
    runtime = _FakeRuntime(
        clean_result=CommandResult(
            args=("lake", "clean"),
            returncode=1,
            stdout="",
            stderr="clean failed",
        ),
        build_result=CommandResult(
            args=("lake", "build"),
            returncode=0,
            stdout="unexpected",
            stderr="",
        ),
    )
    svc = BuildBaseServiceImpl(
        config=ToolkitConfig.from_dict(
            {
                "server": {"default_project_root": str(tmp_path)},
                "build_base": {"default_clean_first": True},
            }
        ),
        runtime=runtime,
        resolver=_FakeResolver(resolved_targets=tuple()),
    )

    resp = svc.run_workspace(BuildWorkspaceRequest.from_dict({}))

    assert resp.success is False
    assert resp.error_message == "clean command failed with return code 1"
    assert resp.returncode == 1
    assert resp.executed_commands == (("lake", "clean"),)
    assert resp.stderr == "clean failed"
    assert runtime.clean_calls == [(tmp_path.resolve(), None)]
    assert runtime.build_calls == []
