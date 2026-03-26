"""External search-provider backends."""

from .manager import SearchAltBackendManager
from .proof_manager import ProofSearchAltBackendManager

__all__ = ["SearchAltBackendManager", "ProofSearchAltBackendManager"]
