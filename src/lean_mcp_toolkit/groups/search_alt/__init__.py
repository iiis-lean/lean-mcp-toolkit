"""Search-alt group service and client factories."""

from .client_http import SearchAltHttpClient
from .factory import create_search_alt_client, create_search_alt_service
from .plugin import SearchAltGroupPlugin
from .service_impl import SearchAltServiceImpl

__all__ = [
    "SearchAltServiceImpl",
    "SearchAltHttpClient",
    "SearchAltGroupPlugin",
    "create_search_alt_service",
    "create_search_alt_client",
]

