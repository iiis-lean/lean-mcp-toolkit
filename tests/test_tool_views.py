from lean_mcp_toolkit.config import ToolMetadataOverrideConfig, ToolViewConfig
from lean_mcp_toolkit.groups.plugin_base import GroupToolSpec
from lean_mcp_toolkit.tool_views import apply_tool_metadata, resolve_tool_view


def test_tool_metadata_add_remove_and_replace_tags() -> None:
    spec = GroupToolSpec(
        group_name="lsp_core",
        canonical_name="lsp.run_snippet",
        raw_name="run_snippet",
        api_path="/lsp/run_snippet",
        description="run snippet",
        tags=("lsp", "read_only"),
    )

    updated = apply_tool_metadata(
        spec,
        {
            "lsp.run_snippet": ToolMetadataOverrideConfig(
                add_tags=("code_exec", "expensive"),
                remove_tags=("read_only",),
            )
        },
    )

    assert updated.tags == ("lsp", "code_exec", "expensive")

    replaced = apply_tool_metadata(
        spec,
        {
            "lsp.run_snippet": ToolMetadataOverrideConfig(
                replace_tags=("custom",),
                add_tags=("safe",),
            )
        },
    )

    assert replaced.tags == ("custom", "safe")


def test_resolve_tool_view_filters_by_group_tool_and_tags() -> None:
    specs = (
        GroupToolSpec(
            group_name="lsp_core",
            canonical_name="lsp.goal",
            raw_name="goal",
            api_path="/lsp/goal",
            description="goal",
            tags=("proof", "read_only"),
        ),
        GroupToolSpec(
            group_name="lsp_core",
            canonical_name="lsp.run_snippet",
            raw_name="run_snippet",
            api_path="/lsp/run_snippet",
            description="run snippet",
            tags=("proof", "code_exec"),
        ),
        GroupToolSpec(
            group_name="search_core",
            canonical_name="lean_explore.find",
            raw_name="find",
            api_path="/search/find",
            description="find",
            tags=("search", "read_only"),
        ),
    )

    view = resolve_tool_view(
        name="proof",
        specs=specs,
        view_config=ToolViewConfig(
            include_groups=("lsp_core",),
            include_tags=("proof",),
            exclude_tags=("code_exec",),
            tool_naming_mode="both",
        ),
        default_tool_naming_mode="prefixed",
    )

    assert tuple(view.specs_by_canonical) == ("lsp.goal",)
    assert view.aliases_by_canonical["lsp.goal"] == ("lsp.goal", "goal")
