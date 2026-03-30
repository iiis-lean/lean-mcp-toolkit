from pathlib import Path

from lean_mcp_toolkit.app.cli_config_store import CliConfigStore, DEFAULT_BASE_URL


def test_cli_config_store_defaults_and_set_value(tmp_path: Path) -> None:
    store = CliConfigStore(tmp_path / "config.toml")

    cfg = store.load()
    assert cfg.default_base_url == DEFAULT_BASE_URL

    updated = store.set_value("default-base-url", "http://127.0.0.1:19090")
    assert updated.default_base_url == "http://127.0.0.1:19090"

    reloaded = store.load()
    assert reloaded.default_base_url == "http://127.0.0.1:19090"
