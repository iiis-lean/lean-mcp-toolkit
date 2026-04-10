from lean_mcp_toolkit.transport.http import HttpConfig



def test_http_config_from_dict() -> None:
    cfg = HttpConfig.from_dict(
        {
            "base_url": "http://127.0.0.1:18080",
            "api_prefix": "/api/v2",
            "tool_view": "proof",
            "timeout_seconds": 12,
            "verify_ssl": False,
            "auth_token": "abc",
            "retry_count": 2,
        }
    )
    assert cfg.base_url == "http://127.0.0.1:18080"
    assert cfg.api_prefix == "/api/v2"
    assert cfg.tool_view == "proof"
    assert cfg.verify_ssl is False
    assert cfg.retry_count == 2



def test_http_config_from_env() -> None:
    env = {
        "LEAN_MCP_TOOLKIT_HTTP__BASE_URL": "http://localhost:9999",
        "LEAN_MCP_TOOLKIT_HTTP__TIMEOUT_SECONDS": "15",
        "LEAN_MCP_TOOLKIT_HTTP__TOOL_VIEW": "search",
        "LEAN_MCP_TOOLKIT_HTTP__VERIFY_SSL": "false",
    }
    cfg = HttpConfig.from_env(env)
    assert cfg.base_url == "http://localhost:9999"
    assert cfg.tool_view == "search"
    assert cfg.timeout_seconds == 15.0
    assert cfg.verify_ssl is False
