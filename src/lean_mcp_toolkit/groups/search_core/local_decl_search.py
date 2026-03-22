"""Local declaration search implementation for search.local_decl.search."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
from typing import Iterable

from ...contracts.search_core import LocalDeclSearchItem

_DECL_HEAD_PATTERN = (
    r"^\s*(?:theorem|lemma|def|axiom|class|instance|structure|inductive|abbrev|opaque)\s+"
)

_INSTALL_HINTS: dict[str, Iterable[str]] = {
    "Windows": ("winget install BurntSushi.ripgrep.MSVC", "choco install ripgrep"),
    "Darwin": ("brew install ripgrep",),
    "Linux": ("sudo apt-get install ripgrep", "sudo dnf install ripgrep"),
}


@dataclass(slots=True)
class LocalDeclSearcher:
    local_decl_max_candidates: int = 2048
    local_decl_require_rg: bool = True

    def search(
        self,
        *,
        project_root: Path,
        query: str,
        limit: int,
        include_dependencies: bool,
        include_stdlib: bool,
    ) -> tuple[LocalDeclSearchItem, ...]:
        self._ensure_rg_available()

        normalized_query = query.strip()
        if not normalized_query:
            return tuple()

        pattern = (
            _DECL_HEAD_PATTERN
            + rf"(?:[A-Za-z0-9_'.]+\.)*{re.escape(normalized_query)}[A-Za-z0-9_'.]*(?:\s|:)"
        )

        cmd = [
            "rg",
            "--json",
            "--no-ignore",
            "--smart-case",
            "--hidden",
            "--color",
            "never",
            "--no-messages",
            "-g",
            "*.lean",
            "-g",
            "!.git/**",
            "-g",
            "!.lake/build/**",
            pattern,
            str(project_root),
        ]

        stdlib_root = self._resolve_stdlib_root(project_root) if include_stdlib else None
        if stdlib_root is not None:
            cmd.append(str(stdlib_root))

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(project_root),
        )

        matches: list[LocalDeclSearchItem] = []
        max_candidates = min(max(limit * 8, limit), max(1, self.local_decl_max_candidates))

        assert process.stdout is not None
        for line in process.stdout:
            if not line:
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue
            if event.get("type") != "match":
                continue
            data = event.get("data") or {}
            line_text = str((data.get("lines") or {}).get("text") or "").lstrip()
            parts = line_text.split(maxsplit=2)
            if len(parts) < 2:
                continue
            kind, name = parts[0], parts[1].rstrip(":")

            path_text = str((data.get("path") or {}).get("text") or "").strip()
            if not path_text:
                continue
            abs_path = Path(path_text)
            if not abs_path.is_absolute():
                abs_path = (project_root / abs_path).resolve()

            origin, display_file = self._classify_origin(
                project_root=project_root,
                abs_file=abs_path,
                stdlib_root=stdlib_root,
            )
            if origin == "dependency" and not include_dependencies:
                continue

            matches.append(
                LocalDeclSearchItem(
                    name=name,
                    kind=kind,
                    file=display_file,
                    origin=origin,
                )
            )
            if len(matches) >= max_candidates:
                process.terminate()
                break

        stdout_text, stderr_text = process.communicate()
        _ = stdout_text
        if process.returncode not in (0, 1) and not matches:
            msg = f"ripgrep exited with code {process.returncode}"
            if stderr_text.strip():
                msg += f": {stderr_text.strip().splitlines()[0]}"
            raise RuntimeError(msg)

        deduped: list[LocalDeclSearchItem] = []
        seen: set[tuple[str, str, str, str]] = set()
        matches.sort(key=lambda item: self._sort_key(item, normalized_query.casefold()))
        for item in matches:
            key = (item.name, item.kind, item.file, item.origin)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= limit:
                break

        return tuple(deduped)

    def _ensure_rg_available(self) -> None:
        if shutil.which("rg"):
            return
        if not self.local_decl_require_rg:
            return
        system = platform.system()
        hints = _INSTALL_HINTS.get(system, ("Install ripgrep manually.",))
        detail = "\n".join(f"  - {line}" for line in hints)
        raise RuntimeError(
            "ripgrep (rg) is required for search.local_decl.search but not found on PATH.\n"
            f"Installation options:\n{detail}"
        )

    @staticmethod
    def _resolve_stdlib_root(project_root: Path) -> Path | None:
        try:
            completed = subprocess.run(
                ["lean", "--print-prefix"],
                cwd=str(project_root),
                text=True,
                capture_output=True,
                check=False,
            )
        except Exception:
            return None
        prefix = completed.stdout.strip()
        if not prefix:
            return None
        src = (Path(prefix).expanduser().resolve() / "src").resolve()
        if not src.exists() or not src.is_dir():
            return None
        return src

    @staticmethod
    def _classify_origin(
        *,
        project_root: Path,
        abs_file: Path,
        stdlib_root: Path | None,
    ) -> tuple[str, str]:
        root = project_root.resolve()
        try:
            rel = abs_file.relative_to(root).as_posix()
            if rel.startswith(".lake/packages/"):
                return "dependency", rel
            return "project", rel
        except ValueError:
            pass

        if stdlib_root is not None:
            try:
                rel_std = abs_file.relative_to(stdlib_root.resolve()).as_posix()
                return "stdlib", rel_std
            except ValueError:
                pass

        return "stdlib", str(abs_file)

    @staticmethod
    def _sort_key(item: LocalDeclSearchItem, query_cf: str) -> tuple[int, int, int, str, str]:
        name_cf = item.name.casefold()
        base_cf = item.name.rsplit(".", 1)[-1].casefold()

        if "." in query_cf:
            if name_cf == query_cf:
                relevance = 0
            elif name_cf.startswith(query_cf):
                relevance = 1
            elif query_cf in name_cf:
                relevance = 2
            elif base_cf == query_cf:
                relevance = 3
            elif base_cf.startswith(query_cf):
                relevance = 4
            elif query_cf in base_cf:
                relevance = 5
            else:
                relevance = 6
        else:
            if name_cf == query_cf or base_cf == query_cf:
                relevance = 0
            elif base_cf.startswith(query_cf):
                relevance = 1
            elif query_cf in base_cf:
                relevance = 2
            elif name_cf.startswith(query_cf):
                relevance = 3
            elif query_cf in name_cf:
                relevance = 4
            else:
                relevance = 5

        origin_rank = 0
        if item.origin == "dependency":
            origin_rank = 1
        elif item.origin == "stdlib":
            origin_rank = 2
        return (relevance, origin_rank, len(base_cf), base_cf, name_cf)


__all__ = ["LocalDeclSearcher"]
