"""Local Loogle manager and adapter."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from ...config import LoogleProviderConfig


class LoogleLocalManager:
    REPO_URL = "https://github.com/nomeata/loogle.git"

    def __init__(self, *, config: LoogleProviderConfig):
        self.config = config
        self.cache_dir = (
            Path(config.local_cache_dir).expanduser().resolve()
            if config.local_cache_dir
            else (Path.home() / ".cache" / "lean-mcp-toolkit" / "loogle")
        )
        self.repo_dir = self.cache_dir / "repo"
        self.index_dir = self.cache_dir / "index"

    @property
    def binary_path(self) -> Path:
        return self.repo_dir / ".lake" / "build" / "bin" / "loogle"

    def ensure_installed(self) -> bool:
        if self.binary_path.exists():
            return True
        if not self.config.local_auto_install:
            return False
        if self.config.local_require_unix and shutil.which("bash") is None:
            return False
        if shutil.which("git") is None or shutil.which("lake") is None:
            return False
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if not self.repo_dir.exists():
            cloned = subprocess.run(
                ["git", "clone", "--depth", "1", self.REPO_URL, str(self.repo_dir)],
                text=True,
                capture_output=True,
                timeout=300,
                check=False,
                cwd=str(self.cache_dir),
            )
            if cloned.returncode != 0:
                return False
        subprocess.run(
            ["lake", "exe", "cache", "get"],
            text=True,
            capture_output=True,
            timeout=600,
            check=False,
            cwd=str(self.repo_dir),
        )
        built = subprocess.run(
            ["lake", "build"],
            text=True,
            capture_output=True,
            timeout=900,
            check=False,
            cwd=str(self.repo_dir),
        )
        return built.returncode == 0 and self.binary_path.exists()

    def query(self, *, query: str, num_results: int, project_root: Path | None) -> list[dict]:
        if not self.ensure_installed():
            raise RuntimeError("local loogle is not available")
        extra_paths = self._discover_project_paths(project_root)
        index_path = self._index_path(project_root)
        if not index_path.exists():
            self._build_index(index_path=index_path, extra_paths=extra_paths)
        cmd = [str(self.binary_path), "--json"]
        if index_path.exists():
            cmd.extend(["--read-index", str(index_path)])
        for path in extra_paths:
            cmd.extend(["--path", str(path)])
        cmd.append(query)
        completed = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
            cwd=str(self.repo_dir),
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "local loogle query failed")
        raw = completed.stdout.strip().splitlines()
        if not raw:
            return []
        import json

        data = json.loads(raw[-1])
        hits = data.get("hits", []) if isinstance(data, dict) else []
        if not isinstance(hits, list):
            return []
        return [
            {
                "name": str(hit.get("name") or ""),
                "type": str(hit.get("type") or ""),
                "module": str(hit.get("module") or ""),
                "raw_payload": dict(hit),
            }
            for hit in hits[:num_results]
            if isinstance(hit, dict)
        ]

    def _index_path(self, project_root: Path | None) -> Path:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        if project_root is None:
            return self.index_dir / "default.idx"
        safe = project_root.name or "project"
        return self.index_dir / f"{safe}.idx"

    def _build_index(self, *, index_path: Path, extra_paths: list[Path]) -> None:
        cmd = [str(self.binary_path), "--write-index", str(index_path), "--json"]
        for path in extra_paths:
            cmd.extend(["--path", str(path)])
        cmd.append("")
        subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=600,
            check=False,
            cwd=str(self.repo_dir),
        )

    def _discover_project_paths(self, project_root: Path | None) -> list[Path]:
        if project_root is None:
            return []
        paths: list[Path] = []
        lake_packages = project_root / ".lake" / "packages"
        if lake_packages.exists():
            for pkg in lake_packages.iterdir():
                lib = pkg / ".lake" / "build" / "lib" / "lean"
                if lib.exists():
                    paths.append(lib)
        project_lib = project_root / ".lake" / "build" / "lib" / "lean"
        if project_lib.exists():
            paths.append(project_lib)
        return sorted(paths)

