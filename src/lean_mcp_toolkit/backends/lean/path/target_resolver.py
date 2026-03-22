"""Resolve user targets into normalized Lean module paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .lean_path import LeanPath
from .target_models import ResolvedTargets


@dataclass(slots=True)
class TargetResolver:
    """Normalize targets and produce ordered module list.

    Rules:
    - supports Lean dot, relative .lean path, relative directory, absolute path
    - directory expansion is non-recursive
    - deduplicates with stable discovery order
    - performs intra-batch topo ordering from `import` dependencies
    """

    def resolve(
        self,
        *,
        project_root: str | Path,
        targets: tuple[str, ...] | list[str] | None,
    ) -> ResolvedTargets:
        root = Path(project_root).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"project_root is not a directory: {root}")

        raw_targets = list(targets) if targets is not None else ["."]

        ordered: list[LeanPath] = []
        seen: set[str] = set()

        for raw in raw_targets:
            for module in self._expand_target(root, str(raw)):
                if module.dot in seen:
                    continue
                seen.add(module.dot)
                ordered.append(module)

        if not ordered:
            return ResolvedTargets(project_root_abs=root, modules=tuple())

        ordered = self._stable_topo_sort(root, ordered)
        return ResolvedTargets(project_root_abs=root, modules=tuple(ordered))

    def _expand_target(self, root: Path, raw: str) -> list[LeanPath]:
        text = raw.strip()
        if not text:
            return []

        if text == ".":
            return self._expand_directory(root)

        path_like = Path(text)
        if path_like.is_absolute():
            return self._expand_absolute_path(root, path_like)

        # Explicit relative file path
        if text.endswith(".lean"):
            rel_file = path_like.as_posix().strip("/")
            module = LeanPath.from_rel_file(rel_file)
            abs_file = module.to_abs_file(root)
            if not abs_file.exists():
                raise ValueError(f"target file does not exist: {text}")
            return [module]

        candidate = (root / path_like).resolve()
        if candidate.exists():
            if candidate.is_dir():
                return self._expand_directory(candidate, root=root)
            if candidate.is_file() and candidate.suffix == ".lean":
                return [LeanPath.from_abs_file(candidate, root)]
            raise ValueError(f"unsupported target path: {text}")

        # Fallback as Lean dot path
        module = LeanPath.from_dot(text)
        abs_file = module.to_abs_file(root)
        if not abs_file.exists():
            raise ValueError(f"dot target does not exist in project_root: {text}")
        return [module]

    def _expand_absolute_path(self, root: Path, abs_path: Path) -> list[LeanPath]:
        resolved = abs_path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"absolute target outside project_root: {abs_path}") from exc

        if resolved.is_dir():
            return self._expand_directory(resolved, root=root)
        if resolved.is_file() and resolved.suffix == ".lean":
            return [LeanPath.from_abs_file(resolved, root)]
        raise ValueError(f"unsupported absolute target: {abs_path}")

    def _expand_directory(self, directory: Path, *, root: Path | None = None) -> list[LeanPath]:
        base_root = root.resolve() if root is not None else directory.resolve()
        entries = sorted(directory.iterdir(), key=lambda p: p.name)
        modules: list[LeanPath] = []
        for entry in entries:
            if entry.is_file() and entry.suffix == ".lean":
                modules.append(LeanPath.from_abs_file(entry.resolve(), base_root))
        return modules

    def _stable_topo_sort(self, root: Path, modules: list[LeanPath]) -> list[LeanPath]:
        index = {module.dot: i for i, module in enumerate(modules)}
        deps: dict[str, set[str]] = {module.dot: set() for module in modules}
        reverse: dict[str, set[str]] = {module.dot: set() for module in modules}

        for module in modules:
            imports = self._parse_imports(module.to_abs_file(root))
            for imp in imports:
                if imp not in index:
                    continue
                deps[module.dot].add(imp)
                reverse[imp].add(module.dot)

        zero = [m.dot for m in modules if not deps[m.dot]]
        zero.sort(key=lambda dot: index[dot])

        result: list[str] = []
        while zero:
            current = zero.pop(0)
            result.append(current)
            followers = sorted(reverse[current], key=lambda dot: index[dot])
            for follower in followers:
                if current in deps[follower]:
                    deps[follower].remove(current)
                    if not deps[follower] and follower not in zero:
                        zero.append(follower)
                        zero.sort(key=lambda dot: index[dot])

        # cycle fallback: append remaining by original order
        if len(result) < len(modules):
            remaining = [module.dot for module in modules if module.dot not in set(result)]
            result.extend(sorted(remaining, key=lambda dot: index[dot]))

        return [LeanPath.from_dot(dot) for dot in result]

    def _parse_imports(self, file_path: Path) -> set[str]:
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            return set()

        imports: set[str] = set()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("--"):
                continue
            if not line.startswith("import "):
                # imports should appear at top; stop on first non-import statement
                break
            payload = line[len("import ") :].split("--", 1)[0].strip()
            if not payload:
                continue
            for token in payload.split():
                token = token.strip()
                if not token:
                    continue
                try:
                    imports.add(LeanPath.from_dot(token).dot)
                except ValueError:
                    continue
        return imports
