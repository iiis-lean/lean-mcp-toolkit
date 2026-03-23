from lean_mcp_toolkit.app import (
    create_declarations_client,
    create_declarations_service,
    create_diagnostics_client,
    create_diagnostics_service,
    create_lsp_assist_client,
    create_lsp_assist_service,
    create_lsp_core_client,
    create_lsp_core_service,
    create_local_toolkit_server,
    create_search_core_client,
    create_search_core_service,
    create_mathlib_nav_client,
    create_mathlib_nav_service,
    create_search_nav_client,
    create_search_nav_service,
    create_toolkit_http_client,
)
from lean_mcp_toolkit.transport.http import HttpConfig



def test_factories_create_instances() -> None:
    service = create_diagnostics_service()
    assert service is not None

    declarations_service = create_declarations_service()
    assert declarations_service is not None

    lsp_core_service = create_lsp_core_service()
    assert lsp_core_service is not None

    lsp_assist_service = create_lsp_assist_service()
    assert lsp_assist_service is not None

    search_core_service = create_search_core_service()
    assert search_core_service is not None

    search_nav_service = create_search_nav_service()
    assert search_nav_service is not None

    mathlib_nav_service = create_mathlib_nav_service()
    assert mathlib_nav_service is not None

    http_cfg = HttpConfig(base_url="http://127.0.0.1:18080")
    client = create_diagnostics_client(http_config=http_cfg)
    assert client.http_config.base_url == "http://127.0.0.1:18080"

    declarations_client = create_declarations_client(http_config=http_cfg)
    assert declarations_client.http_config.base_url == "http://127.0.0.1:18080"

    lsp_core_client = create_lsp_core_client(http_config=http_cfg)
    assert lsp_core_client.http_config.base_url == "http://127.0.0.1:18080"

    lsp_assist_client = create_lsp_assist_client(http_config=http_cfg)
    assert lsp_assist_client.http_config.base_url == "http://127.0.0.1:18080"

    search_core_client = create_search_core_client(http_config=http_cfg)
    assert search_core_client.http_config.base_url == "http://127.0.0.1:18080"

    search_nav_client = create_search_nav_client(http_config=http_cfg)
    assert search_nav_client.http_config.base_url == "http://127.0.0.1:18080"

    mathlib_nav_client = create_mathlib_nav_client(http_config=http_cfg)
    assert mathlib_nav_client.http_config.base_url == "http://127.0.0.1:18080"

    server = create_local_toolkit_server()
    assert server is not None

    toolkit_client = create_toolkit_http_client(http_config=http_cfg)
    assert toolkit_client is not None
