"""Markdown renderers for lsp_core structured responses."""

from __future__ import annotations

from ....contracts.lsp_core import (
    CodeAction,
    LspCodeActionsResponse,
    LspFileOutlineResponse,
    LspGoalResponse,
    LspHoverResponse,
    LspTermGoalResponse,
    OutlineEntry,
)


def render_file_outline_markdown(resp: LspFileOutlineResponse) -> str:
    if not resp.success:
        return _render_error("File Outline", resp.error_message)

    lines: list[str] = ["## File Outline", "", "- success: `true`"]
    if resp.total_declarations is not None:
        lines.append(f"- total_declarations: `{resp.total_declarations}`")

    lines.append("")
    lines.append("### Imports")
    if not resp.imports:
        lines.append("- (none)")
    else:
        lines.extend(f"- `{item}`" for item in resp.imports)

    lines.append("")
    lines.append("### Declarations")
    if not resp.declarations:
        lines.append("- (none)")
    else:
        for entry in resp.declarations:
            lines.extend(_render_outline_entry(entry, indent=0))
    return "\n".join(lines)


def render_goal_markdown(resp: LspGoalResponse) -> str:
    if not resp.success:
        return _render_error("Goal", resp.error_message)

    lines: list[str] = ["## Goal", "", "- success: `true`"]
    if resp.line_context is not None:
        lines.append(f"- line_context: `{resp.line_context}`")

    if resp.goals is not None:
        lines.append("")
        lines.append("### Goals")
        lines.extend(_render_goal_list(resp.goals))

    if resp.goals_before is not None:
        lines.append("")
        lines.append("### Goals Before")
        lines.extend(_render_goal_list(resp.goals_before))

    if resp.goals_after is not None:
        lines.append("")
        lines.append("### Goals After")
        lines.extend(_render_goal_list(resp.goals_after))

    return "\n".join(lines)


def render_term_goal_markdown(resp: LspTermGoalResponse) -> str:
    if not resp.success:
        return _render_error("Term Goal", resp.error_message)

    lines: list[str] = ["## Term Goal", "", "- success: `true`"]
    if resp.line_context is not None:
        lines.append(f"- line_context: `{resp.line_context}`")
    lines.append("")
    lines.append("### Expected Type")
    if resp.expected_type:
        lines.append("```lean")
        lines.append(resp.expected_type)
        lines.append("```")
    else:
        lines.append("- (none)")
    return "\n".join(lines)


def render_hover_markdown(resp: LspHoverResponse) -> str:
    if not resp.success:
        return _render_error("Hover", resp.error_message)

    lines: list[str] = ["## Hover", "", "- success: `true`"]
    if resp.symbol:
        lines.append(f"- symbol: `{resp.symbol}`")

    lines.append("")
    lines.append("### Info")
    if resp.info:
        lines.append("```lean")
        lines.append(resp.info)
        lines.append("```")
    else:
        lines.append("- (none)")

    lines.append("")
    lines.append("### Diagnostics")
    if not resp.diagnostics:
        lines.append("- (none)")
    else:
        for item in resp.diagnostics:
            lines.append(
                f"- [{item.severity}] {item.line}:{item.column} {item.message}"
            )

    return "\n".join(lines)


def render_code_actions_markdown(resp: LspCodeActionsResponse) -> str:
    if not resp.success:
        return _render_error("Code Actions", resp.error_message)

    lines: list[str] = [
        "## Code Actions",
        "",
        "- success: `true`",
        f"- actions: `{len(resp.actions)}`",
    ]
    if not resp.actions:
        lines.append("")
        lines.append("- (none)")
        return "\n".join(lines)

    lines.append("")
    for index, action in enumerate(resp.actions, start=1):
        lines.append(f"### {index}. {action.title}")
        lines.append(f"- is_preferred: `{str(action.is_preferred).lower()}`")
        lines.extend(_render_action_edits(action))
        lines.append("")

    return "\n".join(lines).rstrip()


def _render_error(title: str, error_message: str | None) -> str:
    return "\n".join(
        [
            f"## {title}",
            "",
            "- success: `false`",
            f"- error_message: {error_message or 'unknown error'}",
        ]
    )


def _render_outline_entry(entry: OutlineEntry, *, indent: int) -> list[str]:
    prefix = "  " * max(0, indent)
    line = (
        f"{prefix}- `{entry.name}` ({entry.kind}) "
        f"[{entry.start_line}, {entry.end_line}]"
    )
    if entry.type_signature:
        line += f" : `{entry.type_signature}`"
    out = [line]
    for child in entry.children:
        out.extend(_render_outline_entry(child, indent=indent + 1))
    return out


def _render_goal_list(goals: tuple[str, ...]) -> list[str]:
    if not goals:
        return ["- no goals"]
    out: list[str] = []
    for index, goal in enumerate(goals, start=1):
        out.append(f"- goal {index}:")
        out.append("```lean")
        out.append(goal)
        out.append("```")
    return out


def _render_action_edits(action: CodeAction) -> list[str]:
    if not action.edits:
        return ["- edits: `(none)`"]
    lines = [f"- edits: `{len(action.edits)}`"]
    for edit in action.edits:
        lines.append(
            "- "
            f"[{edit.start_line}:{edit.start_column} -> {edit.end_line}:{edit.end_column}] "
            f"`{edit.new_text}`"
        )
    return lines


__all__ = [
    "render_code_actions_markdown",
    "render_file_outline_markdown",
    "render_goal_markdown",
    "render_hover_markdown",
    "render_term_goal_markdown",
]
