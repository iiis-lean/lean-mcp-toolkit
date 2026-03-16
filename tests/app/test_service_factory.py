from lean_mcp_toolkit.app import (
    create_diagnostics_client,
    create_diagnostics_service,
    create_local_toolkit_server,
    create_toolkit_http_client,
)
from lean_mcp_toolkit.transport.http import HttpConfig



def test_factories_create_instances() -> None:
    service = create_diagnostics_service()
    assert service is not None

    http_cfg = HttpConfig(base_url="http://127.0.0.1:18080")
    client = create_diagnostics_client(http_config=http_cfg)
    assert client.http_config.base_url == "http://127.0.0.1:18080"

    server = create_local_toolkit_server()
    assert server is not None

    toolkit_client = create_toolkit_http_client(http_config=http_cfg)
    assert toolkit_client is not None
