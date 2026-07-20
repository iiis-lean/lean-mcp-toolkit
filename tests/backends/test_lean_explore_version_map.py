import pytest

from lean_mcp_toolkit.backends.lean_explore.version_map import resolve_toolchain_id


@pytest.mark.parametrize(
    ("lean_version", "index_id"),
    [
        ("4.28.0", "20260217_050001"),
        ("4.32.0", "20260714_172516"),
    ],
)
def test_resolve_supported_lean_explore_toolchain(
    lean_version: str,
    index_id: str,
) -> None:
    assert resolve_toolchain_id(lean_version) == index_id
