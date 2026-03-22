"""Declarations group service and client factories."""

from .client_http import DeclarationsHttpClient
from .factory import create_declarations_client, create_declarations_service
from .plugin import DeclarationsGroupPlugin
from .service_impl import DeclarationsServiceImpl

__all__ = [
    "DeclarationsServiceImpl",
    "DeclarationsHttpClient",
    "DeclarationsGroupPlugin",
    "create_declarations_service",
    "create_declarations_client",
]
