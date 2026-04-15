"""Text/AST ``no_sorry`` backend.

This backend performs source-level scanning rather than Lean diagnostics. It is
therefore much lighter, but its messages/positions reflect exact source tokens
and enclosing declaration ranges instead of elaborated diagnostic payloads.
"""

from __future__ import annotations

from pathlib import Path

from ....backends.lean.path import LeanPath, TargetResolver
from ....backends.text_ast import collect_sorries, parse_declarations
from ....config import ToolkitConfig
from ....contracts.diagnostics import DiagnosticItem, LintRequest, NoSorryResult, Position


class TextAstNoSorryInterfaceBackend:
    """Run ``no_sorry`` via lightweight text/AST analysis.

    Semantic notes versus ``lean``:
    - catches ``sorry`` and ``admit`` after masking comments/strings;
    - reports precise token positions in source text;
    - does not require or expose Lean diagnostic state/proof goals.
    """

    backend_name = "text_ast"

    def __init__(
        self,
        *,
        config: ToolkitConfig,
        resolver: TargetResolver,
    ) -> None:
        self.config = config
        self.resolver = resolver

    def run(self, req: LintRequest) -> NoSorryResult:
        if not req.targets:
            return NoSorryResult(
                success=False,
                message="diagnostics.lint.no_sorry requires explicit targets; directory-only invocation is not supported",
                sorries=tuple(),
            )
        try:
            project_root = self._resolve_project_root(req.project_root)
            resolved = self.resolver.resolve(
                project_root=project_root,
                targets=list(req.targets),
            )
            include_content = (
                req.include_content
                if req.include_content is not None
                else self.config.diagnostics.default_include_content
            )
            context_lines = (
                req.context_lines
                if req.context_lines is not None
                else self.config.diagnostics.default_context_lines
            )
        except Exception as exc:
            return NoSorryResult(
                success=False,
                message=str(exc),
                sorries=tuple(),
            )

        findings: list[DiagnosticItem] = []
        for module in resolved.modules:
            try:
                abs_file = (project_root / module.to_rel_file()).resolve()
                text = abs_file.read_text(encoding="utf-8")
            except Exception as exc:
                return NoSorryResult(
                    success=False,
                    message=str(exc),
                    sorries=tuple(),
                )
            parsed = parse_declarations(text=text, module_dot=module.dot)
            sorries = collect_sorries(text=text, parsed_module=parsed)
            if not sorries:
                continue
            lines = text.splitlines()
            for item in sorries:
                content = None
                if include_content:
                    start = max(0, item.pos.line - 1 - max(0, context_lines))
                    end = min(len(lines), item.pos.line + max(0, context_lines))
                    content = "\n".join(lines[start:end])
                message = (
                    f"sorry found in `{item.declaration_name}`"
                    if item.declaration_name
                    else "sorry found"
                )
                findings.append(
                    DiagnosticItem(
                        severity="warning",
                        pos=Position(line=item.pos.line, column=item.pos.column),
                        endPos=(
                            Position(line=item.end_pos.line, column=item.end_pos.column)
                            if item.end_pos is not None
                            else None
                        ),
                        kind="hasSorry",
                        data=message,
                        fileName=module.dot,
                        content=content,
                    )
                )

        success = len(findings) == 0
        return NoSorryResult(
            success=success,
            message=("no sorry found" if success else f"found {len(findings)} sorry diagnostics"),
            sorries=tuple(findings),
        )

    def _resolve_project_root(self, project_root: str | None) -> Path:
        root = project_root or self.config.server.default_project_root
        if not root:
            raise ValueError("project_root is required")
        resolved = Path(root).expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise ValueError(f"project_root is not a directory: {resolved}")
        return resolved


__all__ = ["TextAstNoSorryInterfaceBackend"]
