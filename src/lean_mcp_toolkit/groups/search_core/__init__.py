"""search_core group service and client factories."""

from .client_http import SearchCoreHttpClient
from .factory import create_search_core_client, create_search_core_service
from .plugin import SearchCoreGroupPlugin
from .service_impl import SearchCoreServiceImpl

__all__ = [
    "SearchCoreServiceImpl",
    "SearchCoreHttpClient",
    "SearchCoreGroupPlugin",
    "create_search_core_service",
    "create_search_core_client",
]
